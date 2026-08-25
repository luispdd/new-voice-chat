# Spec 003: Text-to-Speech (TTS) with Piper & Sentence-Boundary Streaming

## Status: Implemented & Verified

## Overview
Converts assistant text responses into natural, low-latency spoken audio using Piper TTS, dynamic HuggingFace Hub voice caching, and sentence-boundary chunking.

## Requirements
1. **Model Management**:
   - Dynamically download ONNX voice models (`.onnx`) and model configurations (`.onnx.json`) from the `rhasspy/piper-voices` repository using `huggingface_hub.hf_hub_download`.
   - Store and cache downloaded model files in the standard local HuggingFace cache directory (`~/.cache/huggingface/hub/`).
   - Configure the ONNX Runtime session with optimized thread limits for CPU inference efficiency (`intra_op_num_threads=2`, `inter_op_num_threads=2`) using `CPUExecutionProvider`.
   - Parse JSON configurations via `PiperConfig.from_dict` and instantiate a ready-to-use `PiperVoice` instance.
2. **Sentence-Boundary Streaming**:
   - As LLM text tokens stream in, buffer them until a sentence boundary (`[.!?\n]`) is reached.
   - Synthesize the complete sentence into 22050Hz 16-bit mono WAV bytes.
   - Transmit sentence audio chunks immediately over WebSocket `/ws/chat` as base64-encoded payloads (`audio_sentence`).
3. **Frontend Queue Player**:
   - `AudioPlaybackService` decodes incoming audio chunks using Web Audio `AudioContext`.
   - Queues and plays audio segments seamlessly in sequence without clicks, pops, or noticeable delays.
   - Supports user interrupt / stop playback action.
   - A 'Muted' icon in the toolbar turns on and off the audio output.   

## API Contracts
- `POST /api/tts`:
  - Request: `application/x-www-form-urlencoded` with `text` field.
  - Response: `audio/wav` binary stream.
- `WebSocket /ws/chat`:
  - Outbound Event: `{ type: "audio_sentence", sentence: string, audio: string (base64) }`

## Usage constraints
1. **Text filtering**:
   - If the response contains text with special characters, like '*', it should not read the word 'asterisk'.
   - If the response contains emoticons, like '😊', it should not read 'smiley face'.