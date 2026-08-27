# 🎙️ Voice Chat Application

An offline-first, low-latency, real-time voice chat application combining a modern frontend, a powerful FastAPI neural inference backend, and MongoDB vector database persistence.

---

## 🚀 Key Features

*   **Zoneless Frontend (Angular 22 + PrimeNG)**: Built using clean standalone components, reactive signals, dynamic RMS volume visualizer, and a custom browser `AudioContext` playback queue.
*   **Real-time Voice VAD**: Browser-based Web Audio Voice Activity Detection (VAD) that captures mic input and automatically sends WAV chunks to the backend on silence.
*   **Fast Neural Speech-to-Text (STT)**: In-memory transcription using `useful-moonshine-onnx` (Moonshine ONNX Tiny) on the local host.
*   **Streaming Text-to-Speech (TTS)**: Low Time-to-First-Audio (TTFA) sentence-boundary streaming synthesis using `piper-tts` (Rhasspy Piper voice models) to respond with voice dynamically.
*   **Vector Search & RAG**: MongoDB persistent sessions, chat history, and embedded semantic search/RAG capabilities using local ONNX embeddings (`fastembed`).
*   **Multi-Provider LLM Integration**: Native support for Ollama, LM Studio, OpenAI API, and OpenRouter.

---

## 🛠️ Prerequisites

Ensure you have the following installed on your system:
*   [Bun](https://bun.sh/) (strictly used for JS/TS dependency management)
*   [uv](https://github.com/astral-sh/uv) (strictly used for Python dependency management)
*   [Docker](https://www.docker.com/) and Docker Compose (for MongoDB)
*   A local LLM provider running (e.g., Ollama or LM Studio) or API credentials for OpenAI/OpenRouter.

---

## 📦 Installation

To set up the project, run the following commands in the root directory:

### 1. Install Monorepo & Frontend Dependencies
```bash
bun install
```

### 2. Install Backend Python Dependencies
```bash
uv sync --project apps/backend
```

### 3. Spin Up the Database
```bash
bun run docker:up
```
*(This command runs `docker compose up -d mongodb` in the background).*

---

## 🚦 Running the Application

For a fully functioning local developer environment, run these three components concurrently:

### 1. Start MongoDB (if not already running)
```bash
bun run docker:up
```

### 2. Run the FastAPI Backend (Dev Mode with SSL)
The backend requires a secure context (SSL) for browser Web Audio and microphone access. You can start the server in development mode using:
```bash
bun run backend
# Or:
bun run backend:dev
```
*Runs the FastAPI server on `https://localhost:8000` with hot-reload enabled, using the repository's `cert.pem` and `key.pem` certificates.*

#### Optional Command-Line Flags
You can configure the target LLM engine and model directly when running `bun run backend` by using the `--` pass-through operator:

*   **Target LM Studio** (Default):
    ```bash
    bun run backend -- --engine lmstudio --model google/gemma-3-4b-it-qat
    ```
*   **Target Ollama**:
    ```bash
    bun run backend -- --engine ollama --model llama3
    ```
*   **Target OpenAI / OpenRouter**:
    ```bash
    bun run backend -- --engine openrouter --api-key <YOUR_KEY> --model meta-llama/llama-3.3-70b-instruct
    ```

Available options include: `--engine` (`lmstudio`, `ollama`, `openai`, `openrouter`), `--model`, `--api-key`, `--base-url`, and `--mongo-uri`.

### 3. Run the Angular Frontend (Dev Mode with SSL)
```bash
bun start
```
*Compiles and serves the application at `https://localhost:4200` with HMR (Hot Module Replacement).*

---

## 🧹 Utility Commands

| Command | Action |
| :--- | :--- |
| `bun run build` | Build the frontend production assets |
| `bun run docker:down` | Stop and remove the MongoDB container |

---

## 🧭 Repository Layout

```
new-voice-chat/
├── apps/
│   ├── backend/            # FastAPI Python application (uv)
│   └── frontend/           # Angular application (bun)
├── .ai/                    # Spec-Driven Development tasks and specifications
├── cert.pem / key.pem      # SSL certificate pair for local HTTPS
├── docker-compose.yml      # MongoDB container infrastructure
├── package.json            # Monorepo scripts & frontend dependencies
├── nx.json                 # Monorepo orchestration configuration
└── tsconfig.base.json      # Base TypeScript configuration
```
