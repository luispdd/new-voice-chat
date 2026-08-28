# Task 011: TTS Toolbar Mute & Playback Control

- **Status**: Completed & Verified
- **Target Component**: `apps/frontend/src/app/core/audio-playback.service.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`
- **Spec Reference**: [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)
- **Audit Reference**: [001-build-review.md](../../audits/001-build-review.md)

## Objective
Implement real-time toolbar audio muting and queue control for assistant speech output:

1. **Toolbar Mute Toggle**:
   - The chat-header component contains, on the left part the name of the conversation and its status (connected / disconnected from the backend), and in the right side a toggle button indicating if the narration is active or not. If the button is off, there should not be narration, only written responses in the main chat window.
   - Add a 'Muted' toggle icon button in the header toolbar (`chat-header .header-right`) allowing the user to turn audio output on and off at any time.

2. **Master Mute State in AudioPlaybackService**:
   - Add an `isMuted` reactive state using Angular Signals and drop mechanism in `AudioPlaybackService`.
   - When muted, immediately silence any currently playing audio and discard incoming `audio_sentence` WebSocket chunks.

3. **Dynamic Unmute/Mute Switching**:
   - Allow toggling mute state seamlessly during a conversation without breaking WebSocket connection or conversation flow.

## Verification
- Unit test suite in `apps/frontend/src/app/core/audio-playback.service.spec.ts` covers signal state reactivity, stopping playback on mute, and discarding queued chunks.
- Unit test suite in `apps/frontend/src/app/chat/chat-container.component.spec.ts` covers toolbar button rendering, state toggle, and UI classes.
- Production bundle build verified via `bun run build`.
