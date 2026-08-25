# Task 004: Piper TTS & HuggingFace Hub Integration

- **Status**: Completed
- **Target Component**: `apps/backend/common/model_manager.py`, `apps/backend/services/tts.py`
- **Spec Reference**: [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)

## Summary
Implemented the model manager module to download and cache Piper ONNX voice checkpoints from `rhasspy/piper-voices` via `huggingface_hub.hf_hub_download`, by default use the `en_GB/cori/high/en_GB-cori-high` model. Configured optimized ONNX CPU execution sessions and implemented sentence-boundary splitting for real-time streamed audio generation. 
