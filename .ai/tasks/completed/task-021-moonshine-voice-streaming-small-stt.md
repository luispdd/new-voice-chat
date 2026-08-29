# Task 021: Upgrade Moonshine STT to `moonshine-ai/moonshine-streaming-small`

- **Status**: Completed
- **Target Component**: `apps/backend/services/stt.py`, `apps/backend/config.py`, `apps/backend/pyproject.toml`
- **Spec Reference**: [002-voice-stt-moonshine.md](../../specs/002-voice-stt-moonshine.md)

## Objective
Upgrade the Speech-to-Text (STT) engine from the legacy `useful-moonshine-onnx` package to the official `moonshine-voice` library, enabling support for `moonshine-ai/moonshine-streaming-small` (`SMALL_STREAMING`) and other modern Moonshine v2 streaming models for superior transcription accuracy and speed.

---

## 🔍 Root Cause Analysis
- `useful-moonshine-onnx` only fetched legacy v1 models from the `moonshine-ai/moonshine` ONNX repository (`tiny` and `base`).
- Requesting `moonshine-ai/moonshine-streaming-small` caused a `404 RemoteEntryNotFoundError` on Hugging Face because modern streaming models belong to the Moonshine v2 family.
- The official `moonshine-voice` package provides direct support for streaming models (`small-streaming`, `tiny-streaming`, `medium-streaming`) with optimized ONNX execution.

---

## Deliverables & Changes
1. **`apps/backend/pyproject.toml`**:
   - Replaced `useful-moonshine-onnx` with `moonshine-voice>=0.1.5`.
2. **`apps/backend/config.py`**:
   - Set default `stt_model_name` to `"moonshine-ai/moonshine-streaming-medium"` (`MEDIUM_STREAMING`).
   - Added `--stt-model` CLI parameter.
3. **`apps/backend/services/stt.py`**:
   - Migrated to `moonshine_voice` (`Transcriber`, `ModelArch`, `get_model_for_language`, `string_to_model_arch`).
   - Implemented flexible model architecture parsing supporting both HuggingFace repo formats and architecture alias names.
   - Singleton model caching and lifespan warmup.
   - Retained 16kHz mono `float32` normalization and dynamic silence trimming.
4. **SDD Specs & Documentation**:
   - Updated `.ai/specs/002-voice-stt-moonshine.md`.
   - Updated `.ai/instructions/backend-python.md`.
