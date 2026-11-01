# Spec 002: Speech-to-Text (STT) with Parakeet TDT 0.6b v2 & Streamed Audio Input

> File name kept for link stability. The engine is no longer Moonshine (removed in task 023) nor Whisper (replaced in task 026).

## Status: Implemented (task 026)

## Overview
Transcribes user speech into text using NVIDIA Parakeet TDT 0.6b v2 (English only, INT8) through `sherpa-onnx` on CPU. The browser detects speech with an AudioWorklet VAD and **streams PCM frames over the WebSocket while the user is speaking**. The backend buffers them and transcribes speculatively during pauses, so the transcript is usually ready when the end-of-turn silence timeout fires.

Benchmark (task 026, 3 user clips of 24-33 s, 8 threads): Parakeet RTF 0.036-0.053 vs Whisper small.en RTF 0.117-0.154, with equal or better accuracy.

## Requirements

1. **Frontend VAD & AudioWorklet** (unchanged behaviour):
   - Uses `AudioWorkletNode`; `ScriptProcessorNode` is forbidden.
   - RMS vocal threshold `silenceThreshold = 0.018`; rolling pre-roll buffer preserves initial consonants.
   - **End of turn after `silenceDurationMs = 1500ms` of silence. This value must NOT be shortened** (users pause to breathe mid-thought).
   - The real `AudioContext.sampleRate` is announced to the backend.

2. **Streamed audio input** (see Spec 001 `/ws/chat` for message contracts):
   - On speech onset the client sends `audio_start` (with `sample_rate`), then binary frames of 16-bit little-endian mono PCM, batched to ~100 ms (pre-roll first, then every VAD chunk including the trailing silence), plus `audio_pause` / `audio_resume` hints (see 3).
   - After the silence timeout (or when the user stops the microphone mid-utterance) the client sends `audio_end` and waits for a `transcript` event. If none arrives within 15 s it shows the transcription-failure message and re-arms the VAD.
   - The client then sends the transcript as a normal `text` message (chat path is unchanged).

3. **Backend utterance buffer & speculative transcription** (`services/stt_stream.py`):
   - One `UtteranceBuffer` per WebSocket connection; `audio_start` resets it.
   - Frames are converted to `float32` (`/ 32768.0`) and resampled to 16 kHz if needed.
   - **The backend never infers silence from signal level** (quiet speech was misread as silence in testing, producing truncated transcripts). The browser VAD, which also decides end of turn, sends `audio_pause` after **700 ms of silence** and `audio_resume` if speech restarts before the end-of-turn timeout.
   - On `audio_pause` the buffered audio is transcribed speculatively in a worker thread (`asyncio.to_thread`), so the event loop is never blocked. `audio_resume` marks that result stale (discarded); a later pause speculates again.
   - On `audio_end`: use the speculative result if still valid (awaiting it if in flight), otherwise transcribe the full buffer. Reply `{ "type": "transcript", "text": string }` (empty string when no speech).

4. **Persistent Model Singleton & Warm-up**:
   - Model: `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` (`encoder/decoder/joiner.int8.onnx`, `tokens.txt`), downloaded via `huggingface_hub.hf_hub_download` (HF cache), loaded with `sherpa_onnx.OfflineRecognizer.from_transducer(..., model_type="nemo_transducer", provider="cpu")`. `STT_MODEL_NAME` / `--stt-model` holds the HF repo id; `STT_THREADS` sets `num_threads`.
   - Initialized and warmed up once at server lifespan startup. Decoding is serialized with a lock (the recognizer is shared by the WebSocket and `/api/transcribe`).

5. **Audio Normalization & Trimming** (shared by both paths):
   - `/api/transcribe` decodes WAV/WebM/MP3 etc. with `pydub` (soundfile fallback) to 16 kHz mono; removes DC offset.
   - No silence trimming: it clipped quiet speech onsets (verified on user clips) and was only needed for Moonshine. Digital-silence (RMS < 0.002) or too-short (< 0.1 s) audio yields an empty transcript.
   - Peak-normalized retry (`(audio / peak) * 0.95`) if audible speech (RMS > 0.01) yields an empty string.
   - Utterances are capped at 60 s.

6. **UI & Response State Handling**:
   - A loading indicator is shown while the transcript is pending.
   - Empty or failed transcription shows an informative message and re-arms the VAD.

## API Contracts
- `POST /api/transcribe`: `multipart/form-data` with `audio` file (WAV / WebM / FLAC...) -> `{ "text": string }` (kept for compatibility).
- `WebSocket /ws/chat` audio messages: see Spec 001.
