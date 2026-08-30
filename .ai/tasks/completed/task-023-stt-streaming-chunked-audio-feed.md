# Task 023: Chunked Audio Feeding for Moonshine Streaming STT Decoder

- **Status**: Completed
- **Target Component**: `./apps/backend/services/stt.py`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)

## Objective
Enhance the Moonshine streaming Speech-to-Text (STT) inference stability and prevent empty or truncated transcriptions by feeding audio to `stream.add_audio()` in 1-second chunks (16,000 samples @ 16kHz) rather than a single monolithic buffer during both initial transcription and peak-normalized retry passes.

---

## 🔍 Root Cause Analysis
- `moonshine-voice` streaming models (`MEDIUM_STREAMING`, `SMALL_STREAMING`, etc.) maintain an internal streaming state across audio chunks ingested via `stream.add_audio()`.
- Passing the entire multi-second audio array (e.g. 5-15 seconds of speech) at once as a single large array list caused streaming decoder state anomalies, buffer overflows, or premature termination resulting in empty text outputs (`""`).
- Ingesting audio in discrete 1-second temporal increments (`chunk_size = 16000` samples) allows the streaming decoder to process audio frame-by-frame smoothly before finalizing the transcription via `stream.stop()`.

---

## Deliverables & Changes
1. **`./apps/backend/services/stt.py`**:
   - In `transcribe_audio()`:
     - Sliced `trimmed_audio` into 1-second chunks (`chunk_size = 16000`) and iteratively fed each chunk into `stream.add_audio(chunk, 16000)`.
     - Applied the identical 1-second chunking loop to `normalized_audio` during the peak-normalized fallback retry pass.
2. **SDD Specs & Guidelines**:
   - Updated `./.ai/specs/002-voice-stt-moonshine.md` (Requirement 4) to specify 1-second chunked streaming audio ingestion.
   - Updated `./.ai/instructions/backend-python.md` to document the streaming decoder feeding requirement.
