# NX Monorepo Architecture Instructions

## Standards & Workspace Layout
- **Orchestrator**: NX (`nx.json`, `package.json`).
- **Package Manager**: Strictly `bun` and `bunx`.
- **Target Defaults**: Build caching, target dependencies, and shared named inputs defined in `nx.json`.
- **TypeScript Config**: Root `tsconfig.base.json` with `"moduleResolution": "bundler"`, referenced by project-specific `tsconfig.app.json` configs.

## Workspace Tree
```
new-voice-chat/
├── apps/
│   ├── backend/            # FastAPI Python application (uv)
│   └── frontend/           # Angular application (bun)
├── .ai/                    # Spec-Driven Development documentation
├── cert.pem / key.pem      # SSL certificate pair
├── docker-compose.yml      # Container infrastructure
├── package.json            # Root workspace scripts & JS deps
├── nx.json                 # Monorepo configuration
└── tsconfig.base.json      # Base TypeScript compiler settings
```

## Library and Component Generation
Per project rules:
- Building blocks must be created using the official generators of each library:
  ```bash
  # Generate new Angular library / component
  bunx nx generate @nx/angular:library libs/<lib-name>
  bunx nx generate @nx/angular:component <component-name> --project=frontend
  ```
- Before running generators, ensure the respective CLI packages are installed (`@nx/angular`, `@nx/js`, `@nx/workspace`).

## Workspace Scripts
| Script | Command | Purpose |
| :--- | :--- | :--- |
| `bun start` | `bunx nx serve frontend` | Launch Angular dev server on port 4200 (SSL) |
| `bun run build` | `bunx nx build frontend` | Production build of frontend |
| `bun run backend` | `PYTHONPATH=. uv run ... apps/backend/main.py` | Launch FastAPI backend |
| `bun run backend:dev`| `PYTHONPATH=. uv run ... uvicorn --reload` | Launch backend with hot reload |
| `bun run docker:up` | `docker compose up -d mongodb` | Start MongoDB container |
| `bun run docker:down`| `docker compose down` | Stop container services |
