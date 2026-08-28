# Task 019: Actionable LLM Provider Error Diagnostics & Graceful Error Display

- **Status**: Completed
- **Target Component**: `apps/backend/services/llm.py`, `.ai/specs/001-core-text-chat.md`
- **Instruction Reference**: [backend-python.md](../../instructions/backend-python.md)
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md)

## Objective
When the configured LLM provider is offline, unreachable, unauthenticated, or misconfigured (e.g. LM Studio not running, Ollama daemon down, OpenAI/OpenRouter network or API key errors), provide specific, actionable diagnostic error messages instead of generic `[Error generating response: Connection error.]`.

## Requirements
1. **Provider Investigation & Diagnostic Mapping**:
   - **LM Studio (`lmstudio`)**: Connection failure -> `[Error: Unable to connect to LM Studio]`
   - **Ollama (`ollama`)**: Connection failure -> `[Error: Unable to connect to Ollama]`
   - **OpenAI (`openai`)**: Connection failure -> `[Error: Unable to connect to OpenAI]`
   - **OpenRouter (`openrouter`)**: Connection failure -> `[Error: Unable to connect to OpenRouter]`
   - **Authentication (`401`)**: `[Error: Authentication failed for {Engine}]`
   - **Model Not Found (`404`)**: `[Error: Model not found on {Engine}]`
   - **Rate Limits (`429`)**: `[Error: Rate limit or quota exceeded for {Engine}]`
   - **Timeouts**: `[Error: Connection timed out for {Engine}]`
   - **Server Errors (`500`)**: `[Error: Server error from {Engine}]`
2. **Generic Exception Formatter**:
   - Implement `format_llm_exception(e, engine, base_url, model)` in `apps/backend/services/llm.py`.
   - Ensure the error text starts with `[Error: ...]` for frontend error detection and TTS suppression.
3. **Spec Updates**:
   - Update `001-core-text-chat.md` with explicit error handling requirements across local and cloud LLM providers.
4. **Verification**:
   - Unit tests covering error categorization for all supported engines and error classes.
