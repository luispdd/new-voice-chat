# Task 028: UI LLM Settings Modal, Environment Configuration, and MongoDB Persistence

- **Status**: Completed & Verified
- **Target Component**: `.env`, `.env.example`, `docker-compose.prod.yml`, `apps/frontend/Dockerfile`, `apps/frontend/nginx.conf`, `apps/backend/config.py`, `apps/backend/db/mongo.py`, `apps/backend/services/llm.py`, `apps/backend/server.py`, `apps/frontend/src/app/core/api.service.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`, `apps/frontend/src/app/chat/chat-container.component.html`, `apps/frontend/src/app/chat/chat-container.component.scss`
- **Instruction Reference**: [backend-python.md](../../instructions/backend-python.md), [frontend-angular.md](../../instructions/frontend-angular.md)
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md), [004-session-persistence-mongo.md](../../specs/004-session-persistence-mongo.md), [007-production-docker-deployment.md](../../specs/007-production-docker-deployment.md)

## Objective
Replace the static startup-only LLM configuration with an interactive settings modal in the UI. The bottom-left sidebar footer (`sidebar-footer` / `.health-badge`), which currently displays the active Engine and Model, becomes a clickable control that opens a modal window where the user can configure the **Engine**, **Base URL**, **Model**, and **API Key**. These settings are persisted in MongoDB and restored automatically on subsequent application/backend startups. Once stored, the API Key must never be returned or displayed in plain text in the modal (treated strictly as a password).

Additionally:
- Externalize all service URLs and default LLM configuration into `.env` / `.env.example` (no hardcoded engine, URLs, or model names in application code):
  - `MONGO_URI=mongodb://mongodb.localhost:27017`
  - `MONGO_DB_NAME=voice_chat`
  - `BACKEND_URL=http://backend.localhost:8000`
  - `LLM_ENGINE=openai`
  - `LLM_BASE_URL=http://127.0.0.1:8888/v1`
  - `LLM_MODEL=unsloth/qwen3.5-4B-GGUF`
  - `LLM_API_KEY=not-needed`
- Allow these default values to still be overridden via the existing CLI parameters (`--engine`, `--base-url`, `--model`, `--api-key`).
- On the first connection, if the LLM server returns an error indicating that an API key is required (`401 Unauthorized` / `AuthenticationError`), automatically open the configuration modal with a prompt message asking the user to enter their API key.
- Configure Docker production deployment (`docker-compose.prod.yml`, `apps/frontend/Dockerfile`, `apps/frontend/nginx.conf`) with `network_mode: host`, `extra_hosts` (`backend.localhost`, `mongodb.localhost`), dynamic Nginx template substitution (`${BACKEND_URL}`), and a `backend` `healthcheck` so the container stack can connect to host-loopback (`127.0.0.1`) LLM servers without startup `502` errors.

## Requirements

### 1. Environment Configuration & CLI Overrides (`.env`, `.env.example`, `apps/backend/config.py`)
- Load root `.env` variables in `apps/backend/config.py` and read `MONGO_URI`, `MONGO_DB_NAME`, `LLM_ENGINE`, `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` from environment variables without hardcoding values in code.
- Preserve full support for CLI parameter overrides (`--engine`, `--base-url`, `--model`, `--api-key`).
- Track whether CLI flags were explicitly passed at launch (`cli_llm_override`) so explicit CLI overrides are respected, while stored MongoDB settings restore automatically when no explicit CLI override is provided.

### 2. MongoDB Persistence (`apps/backend/db/mongo.py`)
- Store LLM configuration in a dedicated `settings` collection using a singleton document (`_id: "llm_config"`):
  ```json
  {
    "_id": "llm_config",
    "engine": "openai",
    "base_url": "http://127.0.0.1:8888/v1",
    "model": "unsloth/qwen3.5-4B-GGUF",
    "api_key": "<secret>",
    "updated_at": "2026-11-02T21:00:00Z"
  }
  ```
- Implement async CRUD helpers:
  - `get_llm_settings() -> Optional[dict[str, Any]]`: Fetches the `"llm_config"` document from `db.settings`.
  - `save_llm_settings(engine: str, base_url: str, model: str, api_key: Optional[str] = None) -> dict[str, Any]`: Upserts the `"llm_config"` document. If `api_key` is `None` or empty string (`""`), preserve any existing stored `api_key` in the database rather than overwriting it with an empty value.

### 3. Backend Runtime Reconfiguration, Auth Probe & Endpoints (`apps/backend/services/llm.py`, `apps/backend/server.py`)
- **Client Reset & Connection/Auth Check (`apps/backend/services/llm.py`)**:
  - Add `reset_llm_client() -> None` to clear the cached `_client` singleton so the next request creates a fresh `AsyncOpenAI` instance with the updated `settings.llm_base_url` and `settings.llm_api_key`.
  - Add `check_llm_auth_status() -> dict[str, Any]` that checks connectivity/authentication against the configured `llm_base_url` and detects if an API key is required (`AuthenticationError` / `PermissionDeniedError` / HTTP 401/403).
- **Startup Restoration (`apps/backend/server.py`)**:
  - During FastAPI `lifespan` startup (immediately after `await init_db()`), load stored settings via `await get_llm_settings()`.
  - If stored settings exist in MongoDB (and were not explicitly overridden via CLI flags), apply `engine`, `base_url`, `model`, and `api_key` to the runtime `settings` object and call `reset_llm_client()`.
- **REST API Endpoints (`apps/backend/server.py`)**:
  - `GET /api/settings/llm`: Returns `{ engine, base_url, model, has_api_key, auth_error, auth_message }` without exposing `api_key`.
  - `PUT /api/settings/llm`: Validates and persists `{ engine, base_url, model, api_key? }`, updates runtime `settings`, resets the LLM client, and returns the sanitized settings payload.

### 4. Frontend UI, Modal & First-Connection API Key Prompt (`apps/frontend/src/app/chat/chat-container.component.*`, `apps/frontend/src/app/core/api.service.ts`)
- Initialize `llmEngine`, `llmBaseUrl`, and `llmModel` signals to empty strings (`''`) in `ChatContainerComponent` and populate them from `GET /api/settings/llm` on startup.
- Convert `.health-badge` in `.sidebar-footer` into a clickable button opening the **LLM Configuration** modal.
- Render the API Key input with `type="password"`, always initialized to `""` when opening the modal, with a masked placeholder when `has_api_key` is `true`.
- Automatically open the modal with an alert banner if `auth_error` is `true` on initial connection or when an authentication error occurs.

### 5. Docker Host Networking, Dynamic Nginx Upstream & Healthcheck (`docker-compose.prod.yml`, `apps/frontend/Dockerfile`, `apps/frontend/nginx.conf`)
- Configure `backend` and `frontend` with `network_mode: host` and `extra_hosts` (`backend.localhost:127.0.0.1`, `mongodb.localhost:127.0.0.1`) so the backend container can reach local LLM servers bound strictly to `127.0.0.1`.
- Use `nginx:alpine` template substitution (`NGINX_ENVSUBST_FILTER=^BACKEND_URL$`) in `apps/frontend/Dockerfile` and `${BACKEND_URL}` in `apps/frontend/nginx.conf`.
- Add a `healthcheck` on `backend` (`${BACKEND_URL}/api/health`) and set `depends_on: backend: condition: service_healthy` on `frontend`.

## Verification Results
- **Backend Unit Tests**: 36/36 passed (`PYTHONPATH=. apps/backend/.venv/bin/python -m pytest apps/backend/tests -q --ignore=apps/backend/tests/test_rag_embeddings.py`).
- **Frontend Unit Tests**: 27/27 passed (`bun run --cwd apps/frontend vitest run`).
- **Frontend Bundle & Type Check**: Clean with `bunx nx build frontend --configuration=development` and `bunx tsc -p apps/frontend/tsconfig.app.json --noEmit`.
- **Docker Stack Verification**: Verified end-to-end with `docker compose -f docker-compose.prod.yml` and live `https://localhost/api/settings/llm` (`200 OK`).

