# Voice Chat Backend

FastAPI service powering the voice AI companion.
- **Speech-to-Text (STT)**: Parakeet TDT 0.6b v2, English (sherpa-onnx, CPU) with streamed audio input
- **Text-to-Speech (TTS)**: Piper TTS with HuggingFace Hub voice model management
- **LLM**: OpenAI SDK client (LM Studio, Ollama, OpenRouter, OpenAI)
- **Database & Storage**: MongoDB (Motor async client)
