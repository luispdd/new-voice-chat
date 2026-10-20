# Task 024: Replace Moonshine STT with Whisper small (whisper.cpp)

## Status: Completed & verified
## Spec: 002-voice-stt-moonshine.md

- Replace `moonshine-voice` with `pywhispercpp` (ggml `small.en`, auto-downloaded).
- Default `STT_MODEL_NAME` is now `small.en`.
- Keep audio decode, silence trimming and peak-normalized retry.
- Update `cache_models.py` and spec 002.
