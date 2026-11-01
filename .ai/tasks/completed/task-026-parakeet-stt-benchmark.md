# Task 026: Benchmark Parakeet TDT 0.6b v2 (English) vs Whisper small.en, then integrate if it wins

- **Status**: Completed & verified
- **Target Component**: Phase 1: scratch benchmark script only. Phase 2 (only if Phase 1 passes): `apps/backend/services/stt.py`, `config.py`, `scripts/cache_models.py`, `pyproject.toml`, frontend audio capture, WebSocket protocol, specs 001/002
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)

## Objective
Evaluate whether `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` (English-only, CPU, INT8) beats the current whisper.cpp `small.en` in accuracy and latency. If the results are good, apply the change (Phase 2) within this same task.

## Phase 1: Benchmark
1. **Isolated environment**: `uv run --no-project --with sherpa-onnx==<newest pinned>` (no project dependency changes).
2. **Model**: `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` in `~/.cache/sherpa-onnx/` (outside the repo).
3. **Clips**: 3-5 user recordings in **FLAC** (decoded with `soundfile`, downmixed to mono and resampled to 16 kHz in the script), including mid-sentence pauses.
4. **Script** (scratch dir): transcribe each clip with whisper.cpp `small.en` and Parakeet (`OfflineRecognizer.from_transducer`, `num_threads=8`); print both texts, wall-clock time, and real-time factor.
5. **Output**: comparison table and a go/no-go recommendation. **Stop and ask the user for review before Phase 2.**

### Phase 1 Results (3 user clips, 8 threads, sherpa-onnx 2.0.1)
| Clip | Audio | Parakeet | Whisper small.en |
|---|---|---|---|
| 1 | 23.7 s | 0.86 s (RTF 0.036) | 3.66 s (RTF 0.154) |
| 2 | 33.1 s | 1.74 s (RTF 0.053) | 3.87 s (RTF 0.117) |
| 3 | 28.9 s | 1.40 s (RTF 0.048) | 4.29 s (RTF 0.148) |

Parakeet is about 2-4x faster. Accuracy is equal or better (clip 1: "working properly" vs Whisper's "the thing properly"). Both handled mid-sentence pauses. Awaiting user confirmation to start Phase 2.

## Phase 2: Integration (only after the user confirms the results)
1. Replace Whisper in `stt.py` with Parakeet (full replacement, confirmed by user). Keep audio decode, silence trimming and warm-up at startup.
2. Update `config.py` / `STT_MODEL_NAME`, `cache_models.py` and the Docker model cache for the new model.
3. **Streaming audio input**: the browser sends 16 kHz PCM frames over `/ws/chat` while the user speaks. The backend transcribes incrementally. The **1.5 s silence timeout is kept** as the end-of-turn rule and is not shortened.
4. Rewrite spec 002 (stale: still describes Moonshine, which task 023/024 removed) and update spec 001 for the new WebSocket audio protocol.
5. Tests for the new STT service and the audio streaming path.
6. The 300-line new-code limit applies. If Phase 2 exceeds it, stop and ask.

## Open Questions
- Where are the FLAC clips? (suggested `./poc/clips/`)
- Phase 2 will need a detailed protocol design (frame size, message format, cancellation/barge-in behaviour). This will be drafted in the spec before any code.

## Phase 2 Implementation Notes
- Backend: `common/model_manager.py` (`load_parakeet_recognizer`), `services/stt.py` (Parakeet, `transcribe_pcm`, `pcm16_to_float32`), new `services/stt_stream.py` (`UtteranceBuffer`), `server.py` (`/ws/chat` handles `audio_start` / binary PCM / `audio_pause` / `audio_resume` / `audio_end` -> `transcript`), `config.py` (`STT_MODEL_NAME` = HF repo id, `STT_THREADS`), `scripts/cache_models.py`, `pyproject.toml` (`pywhispercpp` removed, `sherpa-onnx==2.0.1` added), `docker-compose.prod.yml`.
- STT Tuning: Removed pre-inference silence trimming from `stt.py` because Parakeet handles leading/trailing pauses natively, whereas trimming clipped quiet speech onsets on real user recordings.
- Pause Protocol: The browser VAD sends `audio_pause` at 700ms of silence to trigger speculative transcription, and `audio_resume` if speech restarts before the 1500ms end-of-turn timeout.
- Frontend: `audio-record.service.ts` streams ~100 ms Int16 PCM frames (the 1.5 s silence timeout is unchanged; `exportWAV` removed), `api.service.ts` (`sendWsBinary`), `chat-container.component.ts` (waits for `transcript`, 15 s timeout).
- Docs: specs 001/002, `backend-python.md`, `testing-strategy.md`, READMEs.
- Tests: backend `test_stt_streaming.py` (34 backend tests pass with the Parakeet recognizer mocked), frontend 24 tests pass, `tsc --noEmit` clean.

## Verification Checklist
1. [x] `cd apps/backend && uv sync` (executed by user; `uv.lock` updated with `sherpa-onnx==2.0.1`).
2. [x] Automated unit and integration tests passing (backend 34/34, frontend 24/24).
3. [x] Live voice interaction test: Verified STT transcription works and passes user speech to backend.
