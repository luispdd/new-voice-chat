# Task 010: Fix STT & VAD Lifecycle and Audio Feedback Loop

- **Status**: Completed
- **Target Component**: `apps/frontend/src/app/core/audio-record.service.ts`, `apps/frontend/src/app/chat/chat-container.component.ts`, `apps/frontend/src/app/chat/voice-input.component.ts`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)
- **Audit Reference**: [001-build-review.md](../../audits/001-build-review.md)

## Objective
Fix the Speech-to-Text Voice Activity Detection (VAD) lifecycle, audio recording termination, local feedback issues, and response state flow:

1. **Automatic Stop on Silence**:
   - In `AudioRecordService`, when silence is detected for `silenceDurationMs = 1500ms` after vocal activity (`vadActive`), automatically stop recording and emit the recorded WAV audio chunk.
   - Update `isRecording` state so `ChatContainerComponent` transitions out of the recording state and updates the UI accordingly.

2. **Prevent Microphone Echo/Feedback**:
   - Route `ScriptProcessorNode` to a `GainNode` with `gain.value = 0` before connecting to `destination` (or avoid connecting to destination if browser allows) to prevent microphone input from being played back into the user's speakers/headphones.

3. **Prevent Assistant-to-Mic Acoustic Feedback Loop**:
   - Prevent the microphone from recording or trigger-locking while the assistant is speaking (`audioPlayback.isPlaying`) or voice is processing (`isProcessingVoice`), preventing the assistant's voice from feeding back into STT.

4. **Microphone Toggle UI**:
   - Ensure the microphone toggle button activates/deactivates the VAD system cleanly and reflects listening, processing, and idle states as specified in Spec 002.

5. **Backend Response Detection & VAD Auto-Reactivation**:
   - The UI should display a loading indicator while the LLM is generating the response.
   - In case of error or empty response, it must display an error message in red. The loading indicator must be removed and the VAD system must be reactivated.
   - When the response is received and speech playback finishes, the loading indicator must be removed and the VAD system must be reactivated.

---

## 🔍 Bug Evidences & Verification Failure Analysis (Manual Verification 2026-08-25)

1. **UI Remains in "Listening..." State During Audio Transmission**:
   - **Observed Behavior**: When the user finishes speaking, silence is detected and audio is transmitted to the `POST /api/transcribe` endpoint, but the UI remains stuck displaying "Listening..." instead of updating to "Processing voice...".
   - **Root Cause**: In a Zoneless Angular application, mutating plain mutable component properties (e.g. `this.isRecording = false`, `this.isProcessingVoice = true`) from within asynchronous Web Audio callbacks (`ScriptProcessorNode.onaudioprocess`) or `setTimeout` does not notify Angular's change detection scheduler.

2. **Empty Response Error Message Not Rendered Until Manual Interaction**:
   - **Observed Behavior**: When `POST /api/transcribe` returns an empty response (`""`), the UI does not display the error message automatically. The message `"No speech detected. Please speak into the microphone."` only appears after the user manually clicks the microphone button.
   - **Root Cause**: Pushing new messages to `this.messages` inside asynchronous promises does not signal the Zoneless change detector without Angular Signals or `ChangeDetectorRef.markForCheck()`. Only when a DOM event fires does Angular trigger a check and render the delayed changes.

---

## Required Fixes

1. **Zoneless Architecture Configuration**:
   - Strictly avoid `NgZone` and Zone.js across the entire frontend.
   - Configure `provideZonelessChangeDetection()` in `apps/frontend/src/app/app.config.ts`.

2. **Angular Signals State Management**:
   - Refactor all UI state in `ChatContainerComponent` to Angular Signals (`signal()`, `computed()`):
     - `messages = signal<Message[]>([])`
     - `isRecording = signal<boolean>(false)`
     - `isProcessingVoice = signal<boolean>(false)`
     - `isStreaming = signal<boolean>(false)`
     - `streamingText = signal<string>('')`
     - `isSpeaking = signal<boolean>(false)`
     - `isVadActive = signal<boolean>(false)`
     - `audioLevel = signal<number>(0)`
     - `currentSessionTitle = signal<string>('New Conversation')`
     - `isConnected = signal<boolean>(false)`
     - `isSidebarOpen = signal<boolean>(false)`
   - When Web Audio events, silence timeouts, or STT/WebSocket responses occur, mutating signals via `.set()` or `.update()` automatically notifies Angular's Zoneless change detector to re-render the view in real-time.





