# Task 018: Fix STT Intermittent Empty Transcriptions

- **Status**: Completed (2026-08-27)
- **Target Component**: `apps/backend/services/stt.py`, `apps/backend/config.py`, `apps/frontend/src/app/core/audio-record.service.ts`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)

## Objective
Diagnose and permanently resolve intermittent empty STT transcriptions (`""`) and dropouts during vocal inputs, especially on utterances with leading silence or pauses.

---

## 🔍 Root Cause Analysis

1. **Model Variant Capacity (`moonshine/base` vs `moonshine/tiny`)**:
   - `moonshine/tiny` (~27M params) frequently dropped below the token prediction confidence threshold on conversational/microphone speech, predicting `EOS` immediately.
   - Migrating default model to `moonshine/base` (`MoonshineOnnxModel(model_name="base")`) directly mirrors the proven reference project (`/home/fuchik0ma/code/voice-chat/backend/stt.py`).

2. **Persistent Singleton Caching**:
   - `get_stt_model()` in `stt.py` previously discarded its warmup instance, causing `transcribe_audio()` to reconstruct new ONNX sessions and check HuggingFace Hub on every single chunk/request.
   - Caching `_stt_model` as a persistent global singleton in memory ensures instant inference with 0 session reload overhead.

3. **Leading Silence Early-Termination in Moonshine**:
   - Moonshine's autoregressive decoder attends to frame 0. If an audio clip contains $\ge 2.0$s of leading silence, the attention probabilities collapse to silence and the decoder immediately emits `EOS` (token `2`), abandoning all subsequent speech.
   - Fixed by adding dynamic energy-based `trim_silence()` on the backend with 250ms padding.

4. **Frontend VAD Pre-Roll & Modern AudioWorklet**:
   - Replaced unbounded silence accumulation in `AudioRecordService` with a rolling ~380ms pre-roll buffer that only activates recording when speech onset is detected (`rms > silenceThreshold`).
   - Fully replaced deprecated `ScriptProcessorNode` / `createScriptProcessor` / `onaudioprocess` with modern W3C `AudioWorkletNode` (`AudioWorkletProcessor`).
   - Fixed TypeScript DOM `Uint8Array<ArrayBuffer>` type incompatibility on `AnalyserNode.getByteFrequencyData()`.

---

## Deliverables & Changes

1. **`apps/backend/config.py`**: Default `stt_model_name` set to `"moonshine/base"`.
2. **`apps/backend/services/stt.py`**:
   - Implemented `get_stt_model()` persistent singleton caching.
   - Standardized audio decoding using `pydub.AudioSegment.from_file` (16kHz mono `float32`) with DC offset removal.
   - Added `trim_silence()` to eliminate leading/trailing silence dropouts.
   - Removed destructive 8-second artificial audio splitting in favor of single-pass inference.
3. **`apps/frontend/src/app/core/audio-record.service.ts`**:
   - Migrated to `AudioWorkletNode`.
   - Added rolling pre-roll buffer to prevent leading silence transmission.
   - Resolved `Uint8Array<ArrayBuffer>` TypeScript typing.
4. **SDD Specs & Instructions**:
   - Updated `.ai/specs/002-voice-stt-moonshine.md`.
   - Updated `.ai/instructions/backend-python.md` and `.ai/instructions/frontend-angular.md`.
