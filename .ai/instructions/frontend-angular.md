# Frontend (Angular 22, PrimeNG and TailwindCSS) Instructions

## Standards & Constraints
- **Framework**: Angular 22 (Standalone components, Zoneless-compatible, reactive signals/RxJS).
- **Package Manager**: Strictly use **`bun`** and **`bunx`**. Do not use `npm` or `npx`.
- **UI Library**: PrimeNG (`primeng`, `primeicons`, `@primeuix/themes`).
- **Styling**: SCSS with custom design system tokens, dark glassmorphism, TailwindCSS utility classes and responsive layouts.
- **Root Directory**: `apps/frontend/`
- **Avoid using NgZone**: The frontend must be completely zoneless.
- **Use Angular Signals**: The frontend must use Angular Signals for state management.
- **Use Signal based input and output in components**: Always use signal-based `input()` and `output()` instead of legacy `@Input` and `@Output` decorators.
- **Create independent files for templates, SCSS and test files**: Do not add all content inline in the component class file. Make sure the component generator is configured to create separated template and style files.
- **Unit Test Runner**: **Vitest** with `@analogjs/vite-plugin-angular` using global test APIs (`describe`, `it`, `expect`, `beforeEach`, etc.) configured via `tsconfig.spec.json` and `vite.config.mts`.

## Core Architectural Layers & Responsibilities
- **API & Network Layer**: REST and WebSocket client handling session lifecycle, history retrieval, STT transcription ingestion, and bi-directional real-time chat streaming.
- **Audio Capture & VAD Layer**: Web Audio API microphone capture using modern `AudioWorkletNode` (`AudioWorkletProcessor`), `AnalyserNode` frequency RMS analysis (`Uint8Array<ArrayBuffer>`), rolling pre-roll buffer (~380ms), Voice Activity Detection (VAD), and automatic WAV chunk emission upon silence detection. `ScriptProcessorNode` is strictly forbidden.
- **Audio Playback Queue Layer**: Non-blocking sentence-by-sentence queue playback using browser `AudioContext` buffer scheduling for gapless audio streaming.
- **Chat UI & Orchestration**:
  - Main container orchestrating sidebar drawer, toolbar, message stream, and vocal controls.
  - Interactive scrollable conversation feed with role indicators and speech replay triggers.
  - Push-to-talk and hands-free VAD microphone control toggles.
  - Reactive glowing audio visualizer reflecting listening, speaking, processing, and idle states.

## Key Development Rules
1. **Secure Context**: Web Audio API and audio devices require `https://` (or `localhost`) for microphone permissions. The dev server must always serve over SSL using valid local certificates.
2. **Audio Scheduling**: Incoming base64 WAV chunks from WebSocket streams must be queued and scheduled sequentially to ensure continuous speech without clipping.
3. **Audio Capture**: Always use `AudioWorkletNode` for audio frame sampling. Maintain a rolling pre-roll buffer during VAD listening so initial consonants are intact without transmitting seconds of leading silence.

## Common CLI Commands
```bash
# Start frontend development server
bun start
# Or via NX
bunx nx serve frontend

# Build frontend production bundle
bunx nx build frontend

# Run frontend unit tests with Vitest
bun test
# Or via NX
bunx nx test frontend
```

