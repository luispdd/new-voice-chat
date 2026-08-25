# ADR 003: HuggingFace Hub Piper Voice Model Manager

## Context
Hardcoding local model weight binary paths (`voice_models/*.onnx`) creates repository bloat, requires manual asset distribution, and complicates dynamic multi-voice selection.

## Decision
- Implement a dedicated model manager module (`apps/backend/common/model_manager.py`).
- Utilize `huggingface_hub.hf_hub_download` to download and cache `.onnx` model checkpoints and `.json` configs directly from `rhasspy/piper-voices` into `~/.cache/huggingface/`.
- Configure `onnxruntime.InferenceSession` with thread limits (`intra_op_num_threads=2`, `inter_op_num_threads=2`) and `CPUExecutionProvider` for optimal CPU inference efficiency.

## Consequences
- Clean repository without committing large binary weights.
- Seamless ability to switch and cache new voices on demand.
- Deterministic caching in standard system cache paths.
