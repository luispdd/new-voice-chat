# ADR 002: Docker Containerization vs. Host Development Strategy

## Context
Running all services in Docker during development can slow down edit-reload loops, complicate IDE debugging, and introduce file-watching overhead. Conversely, running database engines locally pollutes the host system.

## Decision
- **MongoDB**: Runs in a **Docker Container** (`docker compose up -d mongodb`) with a persistent volume to isolate database daemons and guarantee identical schemas.
- **FastAPI & Angular**: Run on the **Host Machine** during development (`bun run backend:dev`, `bun start`) to enable instant hot-reload, direct IDE breakpoint debugging, and zero filesystem latency.
- **Local LLMs (Ollama / LM Studio)**: Run as native host daemons to leverage host GPU acceleration without requiring NVIDIA Container Toolkit setups.
- **Production**: Full containerized multi-stage deployments via Docker Compose.

## Consequences
- Maximizes developer velocity while maintaining clean isolation for database and persistence layers.
