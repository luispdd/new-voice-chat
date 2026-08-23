# 🎙️ Voice Chat Application: Architecture & Tooling Analysis

This document provides a comprehensive verification of the roadmap and technical specifications defined in [voice-chat-project-notes.md](file:///home/fuchik0ma/code/new-voice-chat/voice-chat-project-notes.md), incorporating lessons learned from the baseline project [luispdd/voice-chat](https://github.com/luispdd/voice-chat) and adhering to the workspace constraints specified in [AGENTS.md](file:///home/fuchik0ma/code/new-voice-chat/AGENTS.md).

---

## 1. Executive Summary & Evolution from Former Project

The previous project ([luispdd/voice-chat](https://github.com/luispdd/voice-chat)) proved the feasibility of an offline, streaming voice loop using:
* FastAPI backend with Moonshine ONNX STT and Piper TTS.
* Direct integration with local OpenAI-compatible endpoints (LM Studio / Ollama).
* Lightweight vanilla JavaScript frontend with browser Web Audio VAD (Voice Activity Detection).
* Raw PCM/WAV audio streaming over HTTP.

### Key Upgrades for the New Project
1. **NX Monorepo Architecture**: Moving from monolithic scripts to a structured monorepo managing the Angular 22 frontend, FastAPI backend, and shared libraries/generators.
2. **Modern Frontend (Angular 22 + PrimeNG)**: Replacing vanilla JS with modular standalone components, reactive signals, seamless audio playback queues, and polished PrimeNG UI components.
3. **Database & Persistence (MongoDB + Vector Search)**: Transitioning from ephemeral in-memory sessions to persistent sessions, chat history, and embedded RAG document retrieval using MongoDB vector indexes.
4. **Multi-Provider LLM Flexibility**: Native support for Local LLMs (Ollama, LM Studio), OpenAI API, and aggregator gateways (OpenRouter).
5. **Tooling & Environment Standards**: Strict adherence to fast package managers (`bun`/`bunx` for JS/TS, `uv` for Python) and a containerization strategy optimized for developer velocity.

---

## 2. Phase-by-Phase Verification & Execution Guide

### Phase 0 — Setup & Monorepo Foundation
* **Workspace Initialization**:
  * Use `bunx create-nx-workspace` to set up the root monorepo.
  * Integrate `@nx/angular` for Angular 22 app generation and manage backend Python packaging via `uv`.
* **Container Baseline**:
  * Set up `docker-compose.yml` defining MongoDB 7+ with persistent volumes (`mongo_data`) and optional Mongo Express GUI.
* **Security / Secure Context**:
  * The Web Audio API and `MediaRecorder` require `https://` (or `localhost`) to grant microphone access on LAN and mobile devices. Include local SSL certificates (`cert.pem`, `key.pem`) generated via `mkcert` or OpenSSL.

### Phase 1 — Basic Chat (Text-Only MVP)
* **Frontend**:
  * Standalone Angular components for chat interface, message feed, and text prompt input using PrimeNG components (`p-scrollpanel`, `p-inputtext`, `p-button`, `p-card`).
  * Typed API communication layer with FastAPI.
* **Backend**:
  * REST endpoints for chat sessions (`/api/sessions`) and message generation (`/api/chat`).
  * Asynchronous MongoDB ODM/driver (`motor` or `beanie`) for non-blocking persistence.
  * LLM provider connector using `openai` Python SDK (targeting LM Studio `http://localhost:1234/v1`, Ollama `http://localhost:11434/v1`, or OpenRouter/OpenAI).

### Phase 2 — Voice Input (STT) (Use the same tools as the former project if possible)
* **Frontend (VAD & Microphone Capture)**:
  * Port and refine the Web Audio Voice Activity Detection (VAD) algorithm from the former repo.
  * Capture audio chunks (16kHz / 22.05kHz PCM or WAV) using `AudioWorklet` / `MediaRecorder` and send them to the backend when vocal activity ceases.
* **Backend (STT Engine)**:
  * Ingest audio chunks via `POST /api/transcribe` or WebSocket.
  * Execute fast transcription using `useful-moonshine-onnx` (Moonshine ONNX Tiny).
  * Preprocess audio buffers using `soundfile`, `pydub`, and `ffmpeg`.

### Phase 3 — Voice Output (TTS) (Use the same tools as the former project if possible)
* **Backend (Sentence-Streaming Synthesis)**:
  * Piper TTS engine (`piper-tts`) with ONNX voice checkpoints (e.g. `en_US-amy-medium.onnx`).
  * Synthesize audio sentence-by-sentence in real time as LLM text tokens stream in to minimize Time-to-First-Audio (TTFA).
* **Frontend (Audio Playback Service)**:
  * Build an Angular `AudioPlaybackService` utilizing Web Audio API `AudioContext` buffer scheduling.
  * Play incoming audio segments smoothly in sequence without clipping, clicks, or noticeable pauses.

### Phase 4 — RAG System (MongoDB Vector Search)
* **Embedding Model**:
  * Generate high-speed local embeddings using `fastembed` (ONNX-based, low latency, no heavy PyTorch footprint) or third-party embedding APIs.
* **MongoDB Vector Search**:
  * Store chunk text and float embeddings in the `documents` collection.
  * Execute `$vectorSearch` aggregation pipelines to retrieve top-$K$ semantic matches.
* **Prompt Augmentation**:
  * Ground the LLM response by injecting retrieved document snippets into the system prompt.

### Phase 5 — Conversation Memory
* Multi-turn chat context stored in MongoDB per `session_id`.
* Sliding window or token-budgeted memory management with optional background summarization.

### Phase 6 — Real-Time UX & Polish
* Real-time streaming pipeline (SSE or WebSockets) delivering text tokens and audio segments concurrently.
* Visual feedback: Glowing mic state visualizer (waveform or canvas ripple animation), typing indicator, audio playback control (stop/interrupt assistant mid-speech).
* PrimeNG theme customization (dark mode palette, responsive mobile design).

### Phase 7 — Production Deployment
* Multi-stage containerization:
  * **Backend Image**: Python 3.13 + `uv` + pre-cached ONNX models + Piper voices + FFmpeg.
  * **Frontend Image**: Bun build output served via Nginx Alpine reverse proxy.
  * **Database**: MongoDB official container with persistent volume.

---

## 3. Host vs. Docker Strategy (Developer Experience vs. Isolation)

To ensure maximum developer velocity during day-to-day development while keeping the architecture production-ready:

| Service / Tool | Development Mode | Production Mode | Rationale & Trade-offs |
| :--- | :--- | :--- | :--- |
| **MongoDB** | 🐳 **Docker Container** (`docker compose up -d mongodb`) | 🐳 **Docker Container** | **Best in Docker**: Avoids installing MongoDB daemon locally on host. Guarantees version consistency, persistent volume mounting, and clean data teardown. |
| **Mongo Express** (DB GUI) | 🐳 **Docker Container** (Port 8081) | Disabled / Protected | **Best in Docker**: Lightweight browser UI for inspecting collections without local desktop GUI installations. |
| **FastAPI Backend** | 💻 **Host Machine (`uv run uvicorn`)** | 🐳 **Docker Container** | **Best on Host during Dev**: Sub-second hot-reload (`fastapi dev`), instant IDE breakpoint debugging, direct model cache access (`~/.cache/huggingface`), and no container rebuild overhead when modifying Python code. |
| **Angular 22 Frontend** | 💻 **Host Machine (`bun run start` / `bunx nx serve`)** | 🐳 **Docker Container (Nginx)** | **Best on Host during Dev**: Instant HMR (Hot Module Replacement), direct browser dev tools integration, and low memory usage. |
| **Local LLM Engine** (Ollama / LM Studio) | 💻 **Host Daemon** | 💻/🐳 Remote GPU Server or Container | **Best on Host**: Directly utilizes host GPU (CUDA / ROCm / Metal) without requiring complex Docker NVIDIA Container Toolkit passthrough. |

---

## 4. Complete Tooling & Dependency Matrix

In accordance with [AGENTS.md](file:///home/fuchik0ma/code/new-voice-chat/AGENTS.md):

### 📦 Package Managers & CLI Utilities
* **`bun` & `bunx`**: Primary package manager and runner for JavaScript, TypeScript, and NX tools.
* **`uv`**: Primary package manager and virtual environment runner for Python.
* **`nx`**: Monorepo orchestration and building block generator (`bunx nx generate ...`).
* **`docker` & `docker compose`**: Containerization engine for database and production services.
* **`mkcert` / `openssl`**: Local SSL certificate generation for Web Audio HTTPS requirements.

### 🎨 Frontend Ecosystem (Angular 22)
* **Framework**: Angular 22 (`@angular/core`, `@angular/common`, `@angular/router`, `@angular/forms`)
* **UI Component Library**: PrimeNG (`primeng`, `primeicons`, `@primeuix/themes`)
* **Audio Layer**: Web Audio API, `AudioContext`, `AudioWorklet`, `MediaRecorder` (Use the same tools as the former project if possible)
* **Reactive Logic**: TypeScript, Angular Signals, RxJS

### ⚙️ Backend Ecosystem (FastAPI & Python 3.13)
* **Framework & Server**: `fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `websockets`
* **Database Driver**: `motor` (asynchronous MongoDB driver) or `beanie` ODM
* **STT (Speech-to-Text)**: `useful-moonshine-onnx`, `onnxruntime`
* **TTS (Text-to-Speech)**: `piper-tts` (with voice ONNX weights and json config)
* **Audio Preprocessing**: `ffmpeg` (system binary), `soundfile`, `pydub`, `numpy`, `audioop-lts`
* **LLM & RAG**: `openai` SDK (for LM Studio / Ollama / OpenRouter / OpenAI), `fastembed` (for embeddings)

---

## 5. Next Steps for Implementation

1. **Step 1**: Initialize the NX Monorepo workspace with Bun:
   ```bash
   bunx create-nx-workspace@latest new-voice-chat --preset=apps
   ```
2. **Step 2**: Generate the Angular 22 application and install PrimeNG:
   ```bash
   bunx nx generate @nx/angular:app apps/frontend --style=scss --standalone
   bun add primeng primeicons
   ```
3. **Step 3**: Configure the Python backend workspace with `uv`:
   ```bash
   uv init apps/backend
   uv add fastapi uvicorn motor openai useful-moonshine-onnx piper-tts soundfile pydub
   ```
4. **Step 4**: Create `docker-compose.yml` for MongoDB and launch database service:
   ```bash
   docker compose up -d mongodb
   ```
