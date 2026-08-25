# Frontend (Angular 22, PrimeNG and TailwindCSS) Instructions

## Standards & Constraints
- **Framework**: Angular 22 (Standalone components, Zoneless-compatible, reactive signals/RxJS).
- **Package Manager**: Strictly use **`bun`** and **`bunx`**. Do not use `npm` or `npx`.
- **UI Library**: PrimeNG (`primeng`, `primeicons`, `@primeuix/themes`).
- **Styling**: SCSS with custom design system tokens, dark glassmorphism, TailwindCSS utility classes and responsive layouts.
- **Root Directory**: `apps/frontend/`

## Core Modules & Architecture
- `src/app/core/api.service.ts`: REST and WebSocket client handling sessions, messages, STT transcription, and real-time streaming.
- `src/app/core/audio-record.service.ts`: Web Audio API microphone capture with dynamic RMS volume analysis, Voice Activity Detection (VAD), and automatic WAV chunk emission.
- `src/app/core/audio-playback.service.ts`: Non-blocking sentence-by-sentence queue playback using browser `AudioContext` buffer scheduling.
- `src/app/chat/`:
  - `chat-container.component.ts`: Layout orchestrator (session drawer, toolbar, message area, input bar).
  - `chat-history.component.ts`: Scrollable message feed with role badges and replay buttons.
  - `voice-input.component.ts`: Push-to-talk / VAD microphone toggle button.
  - `visualizer.component.ts`: Glowing animated orb reflecting listening, speaking, and idle states.

## Key Development Rules
1. **Secure Context**: Web Audio API and `MediaRecorder` require `https://` (or `localhost`) for microphone permissions. The dev server must always serve over SSL using `cert.pem` and `key.pem`.
2. **Audio Scheduling**: Incoming base64 WAV chunks from WebSocket `/ws/chat` must be decoded and queued into `AudioPlaybackService` to ensure continuous speech without audio clipping.

## Common CLI Commands
```bash
# Start frontend development server
bun start
# Or via NX
bunx nx serve frontend

# Build frontend production bundle
bunx nx build frontend
```
