# Voice Chat Project Setup & Walkthrough

The Voice Chat application has been generated and verified with an **NX Monorepo**, **Angular 22 + PrimeNG** frontend, **FastAPI (Python 3.13 via `uv`)** backend, **Moonshine ONNX STT**, **Piper TTS** with HuggingFace Hub voice caching, and **Docker Compose MongoDB**.

---

## 🏗️ Project Architecture & Components

```
new-voice-chat/
├── apps/
│   ├── backend/                     # FastAPI Backend (Python 3.13 via uv)
│   │   ├── common/
│   │   │   └── model_manager.py     # Piper voice model loader with HuggingFace Hub caching
│   │   ├── db/
│   │   │   └── mongo.py             # Motor async MongoDB ODM & collections
│   │   ├── services/
│   │   │   ├── stt.py               # Moonshine ONNX Speech-to-Text engine
│   │   │   ├── tts.py               # Piper TTS sentence-boundary synthesizer
│   │   │   ├── llm.py               # OpenAI SDK client (LM Studio / Ollama / OpenRouter)
│   │   │   └── rag.py               # MongoDB document ingestion & search
│   │   ├── server.py                # REST endpoints and WebSocket /ws/chat
│   │   ├── main.py                  # Server runner
│   │   └── pyproject.toml           # Backend dependencies managed by uv
│   │
│   └── frontend/                    # Angular 22 Standalone SPA (Bun + NX)
│       ├── src/
│       │   ├── app/
│       │   │   ├── core/
│       │   │   │   ├── api.service.ts            # REST & WebSocket communication
│       │   │   │   ├── audio-playback.service.ts # Web Audio queue player
│       │   │   │   └── audio-record.service.ts   # Web Audio VAD & microphone capture
│       │   │   ├── chat/
│       │   │   │   ├── chat-container.component.ts # Full chat UI layout with sidebar
│       │   │   │   ├── chat-history.component.ts   # Scrollable message bubbles
│       │   │   │   ├── voice-input.component.ts    # Mic button with recording states
│       │   │   │   └── visualizer.component.ts     # Glowing animated audio visualizer
│       │   │   ├── app.config.ts
│       │   │   └── app.component.ts
│       │   ├── styles.scss          # PrimeNG styling, custom tokens, and glassmorphism
│       │   └── index.html
│       └── project.json
│
├── docker-compose.yml               # MongoDB 7+ container configuration
├── cert.pem / key.pem               # Local SSL certificates for Secure Web Audio
├── package.json                     # Bun workspace & scripts
└── nx.json                          # NX workspace configuration
```

---

## 🧪 Verification & Test Results

1. **MongoDB Container**:
   * Running healthy in Docker on port `27017` with persistent volume `voice_chat_mongodb_data`.
2. **Backend Services Tested**:
   * **Piper TTS**: Successfully verified with `hf_hub_download` downloading `rhasspy/piper-voices` and synthesizing 22050Hz 16-bit PCM WAV audio.
   * **Moonshine ONNX STT**: Verified loading model weights and transcribing speech audio.
   * **MongoDB CRUD**: Verified async creation, reading, and cleanup of chat sessions and messages.
3. **Frontend Build**:
   * Angular 22 standalone app built with `bunx nx build frontend` without any compilation errors.

---

## 🚀 How to Run the Application

### 1. Start MongoDB (Docker)
```bash
docker compose up -d mongodb
```

### 2. Start the FastAPI Backend
Using `uv`:
```bash
bun run backend
# Or with auto-reload and SSL on port 8000:
bun run backend:dev
```

* Optional command-line flags:
  * Target LM Studio: `bun run backend -- --engine lmstudio --model google/gemma-3-4b-it-qat`
  * Target Ollama: `bun run backend -- --engine ollama --model llama3`
  * Target OpenRouter / OpenAI: `bun run backend -- --engine openrouter --api-key <YOUR_KEY> --model meta-llama/llama-3.3-70b-instruct`

### 3. Start the Angular 22 Frontend
Using `bun`:
```bash
bun start
# Or directly via NX:
bunx nx serve frontend
```

Navigate to `https://localhost:4200` in your browser.
