# Task 008: Real-time Audio Interruption & Barge-in Handling

- **Status**: Backlog
- **Target Component**: `apps/frontend/src/app/core/`, `apps/backend/server.py`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md), [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)

## Objective
Implement a "barge-in" cancellation flow: when the user starts speaking while the assistant is still playing synthesized speech, immediately stop the client audio queue, cancel in-flight backend LLM/TTS generation for the active session, and prioritize the new user query.
