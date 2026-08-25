# Voice Chat Application: Agent Guidelines & SDD Structure

This repository follows the **Spec-Driven Development (SDD)** methodology. All architectural decisions, component specifications, instructions, and task tracking are maintained in the [`.ai/`](.ai/) directory.

---

## CRITICAL: Task Scope Enforcement
- You are ONLY allowed to modify files related to the ACTIVE task in `.ai/tasks/active/`.
- You MUST NOT implement features from `.ai/tasks/backlog/` or future specs.
- You MUST NOT "prepare" code for upcoming tasks (no stubs, no TODOs for future work).
- If you notice a missing requirement that blocks the current task, STOP and report it. Do NOT guess.
- Before editing any file, ask: "Does this change directly serve the active task?" If no, don't touch it.
- Maximum lines of new code per task: 300. If you exceed this, STOP and ask for confirmation.

## UI Implementation Rule
- NEVER implement UI components without explicit mock data, layout description, or wireframe reference in the spec.
- If the spec says "create a dashboard," that is NOT enough. STOP and request: component hierarchy, data shape, and layout constraints.

---

## 🧭 Spec-Driven Development (SDD) Layout

```
.ai/
├── instructions/            # Reusable implementation instructions
│   ├── backend-python.md    # FastAPI, Python 3.13, uv, Moonshine STT, Piper TTS
│   ├── frontend-angular.md  # Angular 22, PrimeNG, Web Audio VAD & Playback Queue
│   ├── nx-monorepo.md       # NX monorepo, Bun workspaces, generators, and caching
│   └── testing-strategy.md  # Container health, neural models, build and audio smoke tests
├── specs/                   # Single source of truth specifications
│   ├── 001-core-text-chat.md             # LLM streaming & multi-provider engine
│   ├── 002-voice-stt-moonshine.md        # Web Audio VAD & Moonshine ONNX STT
│   ├── 003-voice-tts-piper.md            # Piper TTS & sentence streaming synthesis
│   ├── 004-session-persistence-mongo.md  # MongoDB collections & Motor async driver
│   ├── 005-rag-knowledge-retrieval.md    # Document ingestion & knowledge retrieval
│   └── 006-secure-context-ssl.md         # SSL certificates for Web Audio API
├── tasks/                   # Granular work items & progress tracking
│   ├── backlog/             # Future tasks (FastEmbed, barge-in)
│   ├── active/              # Tasks currently in development
│   ├── review/              # Tasks pending review/verification
│   └── completed/           # Verified implemented tasks (001 - 006)
└── decisions/               # Architecture Decision Records (ADRs)
    ├── 001-nx-monorepo-with-bun-and-uv.md
    ├── 002-docker-vs-host-execution-strategy.md
    ├── 003-huggingface-hub-piper-model-manager.md
    ├── 004-secure-context-ssl-for-web-audio.md
    └── 005-sentence-boundary-streaming-tts.md
```

---

## ⚡ Assistant Rules & Guidelines

1. **Package Managers**:
   - **JavaScript / TypeScript**: Strictly use **`bun`** and **`bunx`**. Never use `npm` or `npx`.
   - **Python**: Strictly use **`uv`** (`uv run`, `uv add`). Never use `pip` or manage venvs manually.
2. **Generators & Building Blocks**:
   - Create new building blocks, components, and libraries using their respective official generators (e.g. `bunx nx generate @nx/angular:...`). Ensure required generator CLI packages are present before running.
3. **Execution Environment**:
   - **MongoDB**: Runs in Docker (`docker compose up -d mongodb`).
   - **FastAPI & Angular**: Run on the host during development (`bun run backend:dev`, `bun start`) to ensure rapid hot-reload and direct audio/IDE debugging.
4. **SDD Workflow**:
   - Before implementing new features, write or update the corresponding spec in [`.ai/specs/`](.ai/specs/).
   - Track progress using granular tasks in [`.ai/tasks/`](.ai/tasks/).
   - Document any major architectural decisions in [`.ai/decisions/`](.ai/decisions/).

## Code Style Constraints
1. To refer to local files, use relative paths starting with `./` or `../`.
2. Avoid absolute paths like `/home/username/...`.