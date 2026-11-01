# Task 027: Fix TTS Sentence Skipping and WebSocket Message Loss

- **Status**: Completed & verified
- **Target Component**: `apps/frontend/src/app/core/api.service.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`, `apps/backend/server.py`
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md), [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)

## Objective
Fix audio sentence playback skipping where intermediate sentences synthesized during active token streaming are dropped on the frontend. Implement Option 2: maintain a message queue signal in `ApiService`, drain and process in order in `ChatContainerComponent`, remove premature `isStreaming` gate on audio chunks, and fix cross-sentence whitespace preservation in `server.py`.

## Verification Results
- **Frontend Tests**: 25/25 passed (`bun run --cwd apps/frontend vitest run`).
- **Frontend Type Check**: Clean with `bunx tsc -p apps/frontend/tsconfig.app.json --noEmit`.
- **Backend Tests**: 34/34 passed (`apps/backend/.venv/bin/python -m pytest apps/backend/tests -q --ignore=apps/backend/tests/test_rag_embeddings.py`).
- **Regression Test**: Added test in `chat-container.component.spec.ts` ensuring `audio_sentence` followed immediately by a `token` in the same batch does not drop the audio.
- **Decoding Order Guarantee**: `AudioPlaybackService` now chains `decodeAudioData` calls sequentially so audio segments cannot be queued or played out of order.
- **User Live Verification**: Confirmed working perfectly in end-to-end voice chat conversation.
