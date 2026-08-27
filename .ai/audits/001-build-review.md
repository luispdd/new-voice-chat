# AUDIT-001: Post-Build Code Review Report

**Date**: 2026-08-25  
**Scope**: Codebase vs Approved Specifications ([001](../specs/001-core-text-chat.md) to [006](../specs/006-secure-context-ssl.md))  
**Task**: [AUDIT-011-post-build-review.md](../tasks/active/AUDIT-011-post-build-review.md)  
**Status**: Completed (Read-Only Analysis)

---

## 1. Executive Summary

A comprehensive architectural and functional audit was performed across the Angular frontend (`apps/frontend`) and FastAPI backend (`apps/backend`) against all approved specifications in `.ai/specs/`. 

While the fundamental components (FastAPI server, MongoDB persistence, Moonshine ONNX STT, Piper TTS, and Web Audio pipelines) are in place and operational, critical deviations and logic flaws were identified in **Speech-to-Text (VAD)** and **Text-to-Speech (Mute & Audio Queue Control)**.

---

## 2. Specification Compliance Matrix

| Spec | Feature Area | Status | Key Findings |
|---|---|---|---|
| **001** | Core Text Chat & Multi-Provider LLM | ⚠️ Partial | REST SSE & WebSocket functional; WebSocket lacks RAG toggle support; Error fallback present. |
| **002** | Speech-to-Text (STT) & VAD | ❌ Major Deviations | VAD does not stop recording after silence; Mic echoes to speaker via `AudioContext.destination`; Continuous mic causes acoustic loop. |
| **003** | Text-to-Speech (TTS) & Piper | ❌ Major Deviations | Missing toolbar Mute icon/toggle; No mute state in `AudioPlaybackService`; Subsequent streaming sentences override stop. |
| **004** | Session Persistence & MongoDB | ✅ Fully Compliant | Schema, Motor driver, indexes, cascading deletion, and lifespan management match spec. |
| **005** | RAG Document Ingestion & Retrieval | ⚠️ Minor Deviation | Ingestion and chunk retrieval work on REST endpoint, but not wired into WebSocket `/ws/chat`. |
| **006** | Secure Context & SSL Configuration | ✅ Fully Compliant | Self-signed SSL certs generated and bound to both Uvicorn and Angular dev server. |

---

## 3. Detailed Findings & Deviations

### 🔴 Spec 002: STT with Moonshine ONNX & VAD

1. **VAD Automatic Recording Termination & State Management** ([audio-record.service.ts](../../apps/frontend/src/app/core/audio-record.service.ts#L85-L93)):
   - **Spec Requirement**: Automatically stops recording and emits a WAV chunk after `silenceDurationMs = 1500ms` of silence.
   - **Current Code**: `silenceTimer` triggers `emitWavChunk()`, which flushes `audioChunks` and emits the Blob, but leaves `this.isRecording = true`. The microphone remains live and capturing audio while the backend is transcribing and the assistant is speaking.
   - **Impact**: The UI remains stuck in "Listening..." state, and speaker output from TTS is captured by the live microphone, triggering infinite feedback loops where the assistant converses with itself.

2. **Microphone Audio Output Feedback** ([audio-record.service.ts:L98](../../apps/frontend/src/app/core/audio-record.service.ts#L98)):
   - **Current Code**: `this.scriptProcessor.connect(this.audioContext.destination);` directly routes the raw microphone stream to the browser audio output.
   - **Impact**: User hears their own voice echoed through their speakers/headphones.

3. **VAD Reset & Speech Detection**:
   - If audio levels never surpass `silenceThreshold = 0.018`, `this.vadActive` stays `false`, and `silenceTimer` never activates. When manually stopped, raw silence is sent to the backend.

---

### 🔴 Spec 003: TTS with Piper & Sentence Streaming

1. **Missing Toolbar Mute Control** ([chat-container.component.ts](../../apps/frontend/src/app/chat/chat-container.component.ts#L61-L79)):
   - **Spec Requirement**: "A 'Muted' icon in the toolbar turns on and off the audio output."
   - **Current Code**: No mute button or state exists in `chat-header`. The only audio control is a conditional "Stop" button in the footer that appears only while `isSpeaking == true`.

2. **Absence of Master Mute State in Audio Playback** ([audio-playback.service.ts](../../apps/frontend/src/app/core/audio-playback.service.ts)):
   - **Spec Requirement**: Audio must be mutable from the UI at any moment.
   - **Current Code**: `AudioPlaybackService` has no `isMuted` state, no `GainNode`, and no method to ignore incoming audio sentences. When `stopPlayback()` is clicked, only the active buffer and current queue are cleared. When the next `audio_sentence` event arrives over WebSocket for the same response, it starts playing out loud immediately.

---

### 🟡 Spec 001 & Spec 005: WebSocket RAG & System Prompt Integration

1. **WebSocket RAG Support** ([server.py:L240-L285](../../apps/backend/server.py#L240-L285)):
   - While `POST /api/chat` supports `{ with_rag: true }`, `WebSocket /ws/chat` does not inspect `with_rag` or query `search_relevant_chunks()`.

---

## 4. Recommended Fixes

### Fix Priority 1: STT & VAD Lifecycle ([Spec 002](../specs/002-voice-stt-moonshine.md))
1. **Auto-Stop Recording on Silence**:
   - In `AudioRecordService`, after `silenceDurationMs` triggers, call `stopRecording()` rather than only clearing buffer arrays, or notify `ChatContainerComponent` to transition out of the recording state.
2. **Prevent Mic Output Feedback**:
   - Route `scriptProcessor` through a muted `GainNode` (`gain.value = 0`) before connecting to `destination` (or use an `AudioWorkletNode`), preventing microphone sound from leaking into speakers.
3. **Mute/Pause Mic during Assistant Playback**:
   - Automatically pause or ignore microphone input while `AudioPlaybackService.isPlaying` is `true` or `isProcessingVoice` is `true`.

### Fix Priority 2: TTS Toolbar Mute & Playback Control ([Spec 003](../specs/003-voice-tts-piper.md))
1. **Add Mute Toggle Button in Toolbar**:
   - Add a button with a speaker/muted icon (`pi-volume-up` / `pi-volume-off`) in `.chat-header .header-right` next to the visualizer.
2. **Add Mute State & Master Gain in `AudioPlaybackService`**:
   - Maintain `isMuted$` (or master `GainNode.gain.value = 0`). When muted, skip enqueuing incoming `audio_sentence` payloads and immediately discard queued audio.
3. **Barge-in / Stop Handling**:
   - When the user interrupts or clicks stop, discard pending WebSocket audio chunks until the next turn.

### Fix Priority 3: WebSocket RAG Parameter ([Spec 005](../specs/005-rag-knowledge-retrieval.md))
1. Support `with_rag: boolean` in inbound WebSocket messages in `server.py` and pass augmented system context to `stream_chat_completion`.
