# Task 016: Fix Backend STT Intermittent Empty Transcriptions

- **Status**: Completed (2026-08-27)
- **Target Component**: `apps/backend/services/stt_service.py`, `apps/backend/routers/transcribe.py`, `apps/frontend/src/app/core/audio-record.service.ts`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)

## Objective
Investigate, diagnose, and fix the root cause of intermittent/random empty transcription responses (`""`) from the `POST /api/transcribe` endpoint when the user speaks into the microphone:

---

## 🔍 Bug Symptoms & Analysis

1. **Intermittent / Random Failures**:
   - Audio is transmitted to `POST /api/transcribe`, but the endpoint frequently returns an empty transcription `{"text": ""}` even when speech was clearly uttered.
   - The issue appears intermittent: it occasionally works for 1–2 messages after refreshing the page or switching conversations, but subsequently fails consistently.

2. **Potential Investigation Areas**:
   - **Frontend WAV Encoding & Sample Rate Handling**:
     - Verify `AudioContext` sample rate vs `ScriptProcessorNode` buffer in `AudioRecordService`.
     - In Web Audio API, if the browser context runs at 44.1kHz or 48kHz and the WAV header declares 16kHz without resampling, Moonshine receives sped-up/pitch-shifted audio resulting in empty token generation.
   - **Backend Audio Preprocessing & Normalization**:
     - In `stt_service.py`, verify how audio files/bytes are decoded (`soundfile`, `scipy`, etc.).
     - Check sample rate conversion to 16,000 Hz, float32 normalization range `[-1.0, 1.0]`, and minimum audio length/padding required by Moonshine ONNX.
   - **Audio Chunk Accumulation & Silence Clearing**:
     - Check `AudioRecordService.audioChunks` lifecycle to ensure previous recording buffers are properly cleared and speech isn't truncated when the silence timer triggers.
   - **Diagnostic Logging**:
     - Add detailed backend debug logging on `/api/transcribe` (audio duration in seconds, sample rate, peak amplitude/RMS, tokens decoded) to facilitate immediate verification.

---

## Required Deliverables

1. Fix audio capture/resampling pipeline between `AudioRecordService` and `STTService` to guarantee 100% reliable 16kHz mono audio input.
2. Fix backend Moonshine ONNX model inference and normalization to reliably transcribe speech inputs.
3. Validate audio transcription end-to-end across multiple consecutive speech inputs.
