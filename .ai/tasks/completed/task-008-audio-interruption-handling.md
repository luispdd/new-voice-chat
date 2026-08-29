# Task 008: Real-time Audio Interruption & Barge-in Handling

- **Status**: Completed & Verified
- **Target Component**: `apps/frontend/src/app/core/`, `apps/frontend/src/app/chat/`, `apps/backend/server.py`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md), [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)

## Objective
Implement a "barge-in" cancellation flow: when the user starts speaking while the assistant is still playing synthesized speech, immediately stop the client audio queue, cancel in-flight backend LLM/TTS generation for the active session, and prioritize the new user query.

## Implementation Summary
1. **Backend Concurrency & Task Cancellation**:
   - Refactored `/ws/chat` in `apps/backend/server.py` to run streaming generation in a background `asyncio.Task`.
   - Enabled real-time handling of `{"type": "interrupt"}` messages and preemption on new `{"type": "text"}` queries, instantly cancelling in-flight LLM/TTS tasks.
   - Added unit test suite `apps/backend/tests/test_audio_interruption.py`.

2. **Frontend Barge-in & Queue Control**:
   - Added `onSpeechDetected` observable in `AudioRecordService` triggered at speech onset when vocal energy exceeds `silenceThreshold`.
   - Connected barge-in in `ChatContainerComponent`: immediately silences active `AudioPlaybackService` playback, resets streaming state, and sends WebSocket interrupt to backend.
   - Maintained VAD active during speech playback so vocal barge-in is possible without cutting microphone capture.
   - Updated UI input controls and Stop button in `chat-container.component.html`.
   - Added unit tests in `chat-container.component.spec.ts`.

## Verification
- Backend unittests: 19/19 tests passing (`PYTHONPATH=. uv run --project apps/backend python3 -m unittest discover apps/backend/tests`).
- Frontend unittests: 21/21 tests passing (`bunx nx test frontend`).
- Frontend production bundle build verified (`bunx nx build frontend`).
