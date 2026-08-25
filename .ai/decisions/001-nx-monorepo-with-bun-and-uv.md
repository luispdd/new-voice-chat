# ADR 001: NX Monorepo with Bun and UV Package Managers

## Context
The project consists of an Angular 22 TypeScript frontend, a Python 3.13 FastAPI backend, and shared container infrastructure. We needed a unified workspace orchestrator while adhering to high-performance package managers.

## Decision
- Use **NX** as the root workspace orchestrator (`nx.json`, `package.json`).
- Strictly use **`bun`** and **`bunx`** for all JavaScript and TypeScript toolchains, generators, and package operations.
- Strictly use **`uv`** for all Python virtual environment management and package resolution (`apps/backend/pyproject.toml`).

## Consequences
- Fast package installs and build caching across the repository.
- Standardized CLI commands across development and CI workflows.
