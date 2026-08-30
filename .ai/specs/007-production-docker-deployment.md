# Spec 007: Production Multi-Stage Docker Builds & Stack Orchestration

## Status: Implemented & Verified

## Overview
Provides a containerized, self-contained production deployment for the entire Voice Chat application stack. Utilizes multi-stage Docker builds, pre-cached neural inference models (Moonshine STT, Piper TTS, FastEmbed), and an Nginx reverse proxy with SSL certificate termination.

## Requirements

1. **Frontend Multi-Stage Container (`apps/frontend/Dockerfile`)**:
   - **Stage 1 (Builder)**: Uses `oven/bun:1.2-alpine` to install dependencies via `--frozen-lockfile` and compile the production bundle (`bunx nx build frontend --configuration=production`).
   - **Stage 2 (Runtime)**: Uses `nginx:alpine` to serve static SPA assets (`dist/apps/frontend/browser`) and route traffic.
   - **SPA Routing**: Configures `try_files $uri $uri/ /index.html;` to support client-side Angular routing.

2. **Nginx Reverse Proxy & SSL Termination (`apps/frontend/nginx.conf`)**:
   - **Port 80**: Permanent HTTP-to-HTTPS redirect (`301 https://$host$request_uri`).
   - **Port 443**: SSL termination using mounted certificates (`/etc/nginx/certs/cert.pem` and `key.pem`).
   - **API Proxy**: Reverse-proxies `/api/` requests to `http://backend:8000/api/`.
   - **WebSocket Proxy**: Reverse-proxies `/ws/` connections with `Upgrade` and `Connection: "Upgrade"` headers and long timeouts (`86400s`).

3. **Backend Container & Model Baking (`apps/backend/Dockerfile`)**:
   - Uses `python:3.13-slim` base image.
   - Installs system audio runtime libraries (`libsndfile1`, `ffmpeg`, `ca-certificates`).
   - Installs `uv` package manager directly via `pip install --no-cache-dir uv`.
   - Synchronizes production dependencies via `uv sync --frozen --no-dev`.
   - **Pre-Caching Build Step**: Runs `apps/backend/scripts/cache_models.py` during image build to download Moonshine STT, Piper TTS voice models, and FastEmbed ONNX weights directly into the image layer, eliminating cold-start latency during runtime deployment.

4. **One-Command Orchestration (`docker-compose.prod.yml`)**:
   - **`mongodb`**: MongoDB 7.0 with persistent named volume `mongodb_data_prod` and healthcheck.
   - **`backend`**: Built from backend Dockerfile, waits for healthy MongoDB, connects to host LLM via `host.docker.internal:host-gateway`.
   - **`frontend`**: Built from frontend Dockerfile, binds ports `80` and `443`, mounts `./cert.pem` and `./key.pem`.

5. **Monorepo Scripts (`package.json`)**:
   - `bun run docker:db:up`: Start MongoDB container for local dev.
   - `bun run docker:db:down`: Stop MongoDB container.
   - `bun run docker:stack:up`: Build and start full production stack in detached mode.
   - `bun run docker:stack:down`: Stop and remove full production stack.
