# Spec 002: Speech-to-Text (STT) with Moonshine ONNX & AudioWorklet VAD

## Status: Implemented & Verified

## Overview
Transcribes user vocal input captured in the browser into text using client-side Voice Activity Detection (VAD) via modern `AudioWorkletNode` and backend Moonshine ONNX (`moonshine/base`) with persistent model session caching and dynamic silence trimming.

## Requirements

1. **Frontend Voice Activity Detection (VAD) & AudioWorklet**:
   - Uses modern W3C `AudioWorkletNode` (`AudioWorkletProcessor`) for glitch-free, off-main-thread audio frame capture. `ScriptProcessorNode` / `createScriptProcessor` is deprecated and strictly forbidden.
   - When activated, monitors microphone stream with `AnalyserNode` using explicit `ArrayBuffer` typing (`Uint8Array<ArrayBuffer>`).
   - Computes RMS volume against the vocal activity threshold (`silenceThreshold = 0.018`).
   - **Rolling Pre-Roll Buffer**: Keeps a rolling pre-roll buffer (~380ms) while waiting for speech to begin. Audio accumulation begins only when speech is detected (`rms > silenceThreshold`), prepending the pre-roll to preserve initial consonants without accumulating unbounded leading silence.
   - Automatically stops recording and emits a 16-bit PCM WAV blob after `silenceDurationMs = 1500ms` of silence.
   - **Sample Rate Handling**: Captures the actual hardware-determined `sampleRate` of the instantiated browser `AudioContext` dynamically and writes it into the WAV header.

2. **Backend Audio Ingestion & Normalization**:
   - Decodes audio payloads (WAV, WebM, MP3, etc.) using `pydub.AudioSegment.from_file(io.BytesIO(audio_bytes))` with `soundfile` fallback.
   - Standardizes to 16,000 Hz, mono (1 channel), 16-bit PCM converted to normalized `float32` array (`np.array(samples, dtype=np.float32) / 32768.0`).
   - Removes DC offset bias: `audio_np = audio_np - np.mean(audio_np)`.

3. **Persistent Model Singleton & Lifespan Warmup**:
   - Model Variant: Defaults to **`moonshine/base`** (`MoonshineOnnxModel(model_name="base")`) for reliable transcription accuracy.
   - Initializes and warms up the STT model singleton once during server lifespan startup. Reconstructive per-request ONNX session reloading is strictly avoided.

4. **Dynamic Silence Trimming & Single-Pass Inference**:
   - **Dynamic Silence Trimming**: Executes dynamic silence trimming with adaptive RMS thresholding and 250ms pre/post margin before inference. Eliminates Moonshine decoder `EOS` (token `2`) early-termination caused by leading silence $\ge 2.0$s.
   - **Single-Pass Inference**: Transcribes complete audio utterances directly in a single inference pass. Arbitrary mid-speech chunk slicing (e.g. at 8s) is forbidden as it breaks active phonemes and causes token dropouts.
   - **Fallback Retry**: Performs peak-normalized retry (`(audio / peak) * 0.95`) if an audible utterance ($\text{RMS} > 0.01$) yields an empty decoded string.
   - Limits single utterances to 60 seconds maximum.

5. **UI & Response State Handling**:
   - Displays a loading indicator while the LLM and STT process responses.
   - If empty or erroneous audio is received, displays an informative message and automatically re-arms the VAD system.

## API Contracts
- `POST /api/transcribe`:
  - Request: `multipart/form-data` with `audio` file payload (WAV / WebM).
  - Response: `{ "text": string }`

