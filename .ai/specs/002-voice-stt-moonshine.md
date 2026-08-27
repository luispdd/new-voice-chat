# Spec 002: Speech-to-Text (STT) with Moonshine ONNX & VAD

## Status: Implemented & Verified

## Overview
Transcribes user vocal input captured in the browser into text using client-side Voice Activity Detection (VAD) and Moonshine ONNX (`useful-moonshine-onnx`) in the backend.

## Requirements
1. **Frontend Voice Activity Detection (VAD)**:
   - A button with an icon with the shape of a microphone activates and deactivates the VAD system.
   - When activated, it monitors microphone stream with `AnalyserNode`.
   - Computes RMS volume and detects vocal activity threshold (`silenceThreshold = 0.018`).
   - Automatically stops recording and emits a WAV chunk after `silenceDurationMs = 1500ms` of silence.
   - **Sample Rate Handling**: Captures the actual hardware-determined `sampleRate` of the instantiated browser `AudioContext` dynamically. When exporting the WAV file, declares the true `sampleRate` in the WAV header rather than hardcoding `16000`, preventing speed/pitch distortions on the backend.
2. **Audio Normalization**:
   - Resamples multi-channel or variable sample rate audio into 16kHz mono `float32` array (`audio_bytes_to_float32`).
   - **Resampling Conversion**: High-precision conversion must clip inputs to `[-1.0, 1.0]`, scale to 16-bit signed integer PCM, perform resampling via `AudioSegment(..., sample_width=2)` from `pydub`, and convert back to normalized `float32` by dividing by `32768.0`. Direct resampling on raw float32 bytes must be avoided to prevent signal scrambling.
3. **Transcription Inference & Audio Chunking**:
   - Backend service `apps/backend/services/stt.py` calls `moonshine_onnx.transcribe(audio_data, model="moonshine/tiny")`.
   - **Long Sentence Audio Chunking**: Direct ONNX inference of Moonshine has a shape/attention sequence constraint (returns `''` on inputs longer than ~9-10 seconds). The backend must segment incoming audio into chunks of at most `8.0` seconds:
     - Search window splits must occur at local silence points (100ms window with the lowest absolute energy) to prevent splitting middle of words.
     - Transcribe each chunk independently and join the decoded text blocks with a space.
   - **Duration Guard & Diagnostics**: Truncate segments longer than `60` seconds to fit model limits. Log diagnostic details (original format, sample rate, channels, duration, peak amplitude, and RMS value) for debugging.
   - Returns sanitized transcription string.
4. **Warmup**:
   - Pre-warms the tokenizer and model during server startup via `get_stt_model()`.
5. **Detect backend response**:
   - The UI should display a loading indicator while the LLM is generating the response.
   - In case of error or empty response, it must display an error message in red. The loading indicator must be removed and the VAD system must be reactivated.
   - If the response is received the loading indicator must be removed and the VAD system must be reactivated.

## API Contracts
- `POST /api/transcribe`:
  - Request: `multipart/form-data` with `audio` file payload (WAV / WebM).
  - Response: `{ text: string }`
