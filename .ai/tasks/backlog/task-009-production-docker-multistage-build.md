# Task 009: Production Multi-Stage Docker Builds & Nginx Reverse Proxy

- **Status**: Backlog
- **Target Component**: `apps/frontend/Dockerfile`, `apps/backend/Dockerfile`, `docker-compose.prod.yml`
- **Spec Reference**: [006-secure-context-ssl.md](../../specs/006-secure-context-ssl.md)

## Objective
Create multi-stage production Dockerfiles:
1. `apps/frontend/Dockerfile`: Build Angular SPA with Bun, serve with Nginx Alpine, and configure reverse-proxy rules for `/api` and `/ws`.
2. `apps/backend/Dockerfile`: Minimal Python 3.13 image with `uv`, pre-cached ONNX models, and Piper TTS voices.
3. `docker-compose.prod.yml`: One-command production deployment with persistent MongoDB volume and Nginx SSL certificates.
