# Spec 002: Speech-to-Text (STT) with Moonshine ONNX & VAD

## Status: Implemented & Verified

## Overview
Transcribes user vocal input captured in the browser into text using client-side Voice Activity Detection (VAD) and Moonshine ONNX (`useful-moonshine-onnx`) in the backend.

## Requirements
1. **Frontend Voice Activity Detection (VAD)**:
   - A button with an icon with the shape of a microphone activates and deactivates the VAD system.
   - When activated, it monitors microphone stream with `AnalyserNode`.
   - Computes RMS volume and detects vocal activity threshold (`silenceThreshold = 0.018`).
   - Automatically stops recording and emits a WAV chunk after `silenceDurationMs = 2800ms` of silence.
2. **Audio Normalization**:
   - Resamples multi-channel or variable sample rate audio into 16kHz mono `float32` array (`audio_bytes_to_float32`).
3. **Transcription Inference**:
   - Backend service `apps/backend/services/stt.py` calls `moonshine_onnx.transcribe(audio_data, model="moonshine/tiny")`.
   - Returns sanitized transcription string.
4. **Warmup**:
   - Pre-warms the tokenizer and model during server startup via `get_stt_model()`.

## API Contracts
- `POST /api/transcribe`:
  - Request: `multipart/form-data` with `audio` file payload (WAV / WebM).
  - Response: `{ text: string }`
