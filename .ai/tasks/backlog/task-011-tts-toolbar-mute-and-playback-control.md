# Task 011: TTS Toolbar Mute & Playback Control

- **Status**: Backlog (Next Priority after Task 010)
- **Target Component**: `apps/frontend/src/app/core/audio-playback.service.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`
- **Spec Reference**: [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)
- **Audit Reference**: [001-build-review.md](../../audits/001-build-review.md)

## Objective
Implement real-time toolbar audio muting and queue control for assistant speech output:

1. **Toolbar Mute Toggle**:
   - Add a 'Muted' toggle icon button in the header toolbar (`chat-header .header-right`) allowing the user to turn audio output on and off at any time.

2. **Master Mute State in AudioPlaybackService**:
   - Add an `isMuted` reactive state and master gain control / drop mechanism in `AudioPlaybackService`.
   - When muted, immediately silence any currently playing audio and discard incoming `audio_sentence` WebSocket chunks.

3. **Dynamic Unmute/Mute Switching**:
   - Allow toggling mute state seamlessly during a conversation without breaking WebSocket connection or conversation flow.
