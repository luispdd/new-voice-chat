# Task 010: Fix STT & VAD Lifecycle and Audio Feedback Loop

- **Status**: Active (Priority 1)
- **Target Component**: `apps/frontend/src/app/core/audio-record.service.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`, `apps/frontend/src/app/chat/voice-input.component.ts`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)
- **Audit Reference**: [001-build-review.md](../../audits/001-build-review.md)

## Objective
Fix the Speech-to-Text Voice Activity Detection (VAD) lifecycle, audio recording termination, and local feedback issues:

1. **Automatic Stop on Silence**:
   - In `AudioRecordService`, when silence is detected for `silenceDurationMs = 2800ms` after vocal activity (`vadActive`), automatically stop recording and emit the recorded WAV audio chunk.
   - Update `isRecording` state so `ChatContainerComponent` transitions out of the recording state and updates the UI accordingly.

2. **Prevent Microphone Echo/Feedback**:
   - Route `ScriptProcessorNode` to a `GainNode` with `gain.value = 0` before connecting to `destination` (or avoid connecting to destination if browser allows) to prevent microphone input from being played back into the user's speakers/headphones.

3. **Prevent Assistant-to-Mic Acoustic Feedback Loop**:
   - Prevent the microphone from recording or trigger-locking while the assistant is speaking (`audioPlayback.isPlaying`) or voice is processing (`isProcessingVoice`), preventing the assistant's voice from feeding back into STT.

4. **Microphone Toggle UI**:
   - Ensure the microphone toggle button activates/deactivates the VAD system cleanly and reflects listening, processing, and idle states as specified in Spec 002.
