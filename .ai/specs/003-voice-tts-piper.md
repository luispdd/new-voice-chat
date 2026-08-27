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
   - Audio playback queue decodes incoming audio chunks using Web Audio `AudioContext`.
   - Queues and plays audio segments seamlessly in sequence without clicks, pops, or noticeable delays.
   - Supports user interrupt / stop playback action.
   - A 'Muted' icon in the toolbar turns on and off the audio output.   

## API Contracts
- `POST /api/tts`:
  - Request: `application/x-www-form-urlencoded` with `text` field.
  - Response: `audio/wav` binary stream.
- `WebSocket /ws/chat`:
  - Outbound Event: `{ type: "audio_sentence", sentence: string, audio: string (base64) }`

## Usage constraints & Text Sanitization
1. **Text Sanitization Pipeline**:
   - All text must pass through a sanitization filter prior to speech synthesis and audio streaming.
   - **Markdown Removal**: Strip link URLs (`[text](url)` -> `text`), image tags (`![alt](url)` -> `""`), inline/fenced code markers, header hashes (`#`), blockquotes (`>`), and bullet markers (`*`, `-`, `+`).
   - **Special Characters & Markdown Bloat**: Strip standalone asterisks (`*`), bold/italic formatting (`**text**`, `*text*`, `_text_`), strikethrough (`~~text~~`), hashtags (`#`), tildes (`~`), pipes (`|`), brackets, and backslashes so words like "asterisk", "hash", or "pipe" are never vocalized.
   - **Emojis & Unicode Symbols**: Strip Unicode emoji blocks (`0x1F000+`), Dingbats, miscellaneous symbols, decorative glyphs (`•`, `★`, `✓`), invisible format controls, and unreadable characters so symbols are never vocalized (e.g. as "smiley face" or "rocket").
   - **Emoticons & Kaomojis**: Strip ASCII emoticons (e.g. `:)`, `:-D`, `:(`, `;-)`, `:P`, `xD`, `<3`) and kaomojis (e.g. `¯\_(ツ)_/¯`, `ಠ_ಠ`, `(^_^)`) before speech synthesis.
   - **Punctuation & Empty Payload Handling**: Collapse whitespace, remove empty parentheses/brackets, and normalize repeated punctuation (`!!` -> `!`). Treat inputs without speakable text as silence by returning empty audio data or skipping audio sentence generation rather than raising errors.