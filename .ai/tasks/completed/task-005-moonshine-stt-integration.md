# Task 005: Moonshine ONNX Speech-to-Text Integration

- **Status**: Completed
- **Target Component**: `apps/backend/services/stt.py`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)

## Summary
Integrated `useful-moonshine-onnx` for local transcription. Implemented audio normalization to 16kHz mono float32 arrays via `soundfile`, `pydub`, and `audioop-lts` on Python 3.13. Added server lifespan model warmup.
