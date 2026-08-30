# Task 009: Production Multi-Stage Docker Builds & Nginx Reverse Proxy

- **Status**: Completed
- **Target Component**: `apps/frontend/Dockerfile`, `apps/backend/Dockerfile`, `docker-compose.prod.yml`
- **Spec Reference**: [006-secure-context-ssl.md](../../specs/006-secure-context-ssl.md), [007-production-docker-deployment.md](../../specs/007-production-docker-deployment.md)

## Objective
Create multi-stage production Dockerfiles:
1. `apps/frontend/Dockerfile`: Build Angular SPA with Bun, serve with Nginx Alpine, and configure reverse-proxy rules for `/api` and `/ws`.
2. `apps/backend/Dockerfile`: Minimal Python 3.13 image with `uv`, pre-cached ONNX models, and Piper TTS voices.
3. `docker-compose.prod.yml`: One-command production deployment with persistent MongoDB volume and Nginx SSL certificates.

## Implementation Details
- `apps/frontend/Dockerfile`: Multi-stage build leveraging `oven/bun:1.2-alpine` for the build step and `nginx:alpine` for the serving image.
- `apps/frontend/nginx.conf`: Nginx server with SSL on port 443, HTTP-to-HTTPS redirect on port 80, SPA fallback routing, and reverse-proxying for `/api/` and `/ws/`.
- `apps/frontend/src/app/core/api.service.ts`: Updated to support reverse proxy routing in production while keeping port 8000 direct access during local port 4200 dev.
- `apps/backend/scripts/cache_models.py`: Utility script to download and pre-cache Moonshine STT, Piper TTS, and FastEmbed ONNX models during container image build.
- `apps/backend/Dockerfile`: Production Python 3.13 slim image using `uv`, installing system audio libs (`libsndfile1`, `ffmpeg`), and executing `cache_models.py` in the build layer.
- `docker-compose.prod.yml`: Full stack definition with MongoDB (`mongodb_data_prod`), Python backend, and Frontend Nginx with SSL certificate volume mounts.
- `package.json`: Added `docker:db:up`/`down` and `docker:stack:up`/`down` scripts.

## Verification
- Frontend production build (`bun run build`) verified.
- Frontend test suite (23/23 tests) verified.
- Backend test suite (37/37 tests) verified.
