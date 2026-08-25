# Task 013: Instruct LLM and Filter Unreadable Elements

- **Status**: Backlog
- **Target Component**: `apps/backend/services/llm.py`, `apps/backend/services/tts.py`, `apps/backend/server.py`
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md), [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)

## Objective
Instruct the LLM and filter responses to prevent unreadable unicode characters, emojis, emoticons, and markdown symbols from being generated or vocalized:

1. **LLM System Prompt Instructions**:
   - Update the system prompt in `apps/backend/services/llm.py` to explicitly instruct the model not to output emojis (e.g. `😊`, `🚀`), ASCII emoticons (e.g. `:)`, `xD`), asterisks, bullet lists, markdown bloat, or unreadable unicode characters.
   - Emphasize plain, natural conversational phrasing suited for voice-first interactions.

2. **TTS Text Sanitization & Fallback Filtering**:
   - In `apps/backend/services/tts.py`, add a sanitization filter that strips markdown symbols (like `*`, `#`, `_`), emoticons, and unicode emojis before sentences are sent to Piper TTS.
   - Ensure Piper TTS never vocalizes words like "asterisk" or "smiley face" if any such tokens appear in the text stream.
