# Testing & Verification Strategy

## Multi-Layer Verification Strategy
The system consists of audio pipelines, streaming WebSockets, local ONNX neural models, and asynchronous database connections. Testing is structured across three layers:

### 1. Database & Infrastructure Layer
- **Container Healthcheck**: Verify MongoDB container status and connectivity:
  ```bash
  docker compose ps
  docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"
  ```
- **Async Driver Verification**: Test session and message insertion/querying with Motor in `apps/backend/db/mongo.py`.

### 2. Neural Audio & Synthesis Layer
- **Piper TTS**: Verify `hf_hub_download` retrieves model and config files and synthesizes non-empty 22050Hz 16-bit PCM WAV chunks.
- **Moonshine ONNX STT**: Test `moonshine_onnx.transcribe` with synthetic/recorded WAV audio to ensure `float32` normalization and transcription work without crashing.
- **End-to-End Test Script**:
  ```bash
  PYTHONPATH=. uv run --project apps/backend python3 -c "
  import asyncio
  from apps.backend.db.mongo import init_db, create_session, close_db
  from apps.backend.services.tts import text_to_wav_bytes
  from apps.backend.services.stt import transcribe_audio
  async def run():
      await init_db()
      wav = text_to_wav_bytes('Testing speech')
      assert len(wav) > 1000
      transcription = transcribe_audio(wav)
      await close_db()
      print('✅ All backend component checks passed!')
  asyncio.run(run())
  "
  ```

### 3. Frontend & Build Layer
- **Frontend Unit Tests (Vitest)**:
  ```bash
  bun test
  # Or via NX
  bunx nx test frontend
  ```
- **TypeScript & Angular Compilation**:
  ```bash
  bunx nx build frontend
  ```
- **Browser Web Audio Smoke Testing**:
  1. Open `https://localhost:4200` (accept self-signed certificate).
  2. Click microphone button -> grant audio permission -> speak into microphone.
  3. Verify Voice Activity Detection triggers audio chunk emission.
  4. Verify assistant audio is streamed sentence-by-sentence and played back smoothly through `AudioPlaybackService`.
