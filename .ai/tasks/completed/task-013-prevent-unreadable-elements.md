# Task 013: Instruct LLM and Filter Unreadable Elements

- **Status**: Completed (2026-08-27)
- **Target Component**: `apps/backend/services/llm.py`, `apps/backend/services/tts.py`, `apps/backend/server.py`
- **Spec Reference**: [001-core-text-chat.md](../../specs/001-core-text-chat.md), [003-voice-tts-piper.md](../../specs/003-voice-tts-piper.md)

---

## 🔍 Objectives & Requirements

1. **LLM System Prompt Instructions**:
   - Explicitly instruct the model not to output emojis (e.g. `😊`, `🚀`), ASCII emoticons (e.g. `:)`, `xD`), asterisks, bullet lists, markdown bloat, or unreadable unicode characters.
   - Emphasize plain, natural conversational phrasing suited for voice-first interactions.

2. **TTS Text Sanitization & Fallback Filtering**:
   - In `apps/backend/services/tts.py`, add a sanitization filter that strips markdown symbols (like `*`, `#`, `_`), emoticons, kaomojis, decorative symbols, and unicode emojis before sentences are sent to Piper TTS.
   - Ensure Piper TTS never vocalizes words like "asterisk" or "smiley face" if any such tokens appear in the text stream.
   - Ensure WebSocket streaming and REST endpoints apply sanitization and validate non-empty spoken content.

---

## 🛠️ Implemented Solutions

1. **Strict Voice LLM System Prompt (`apps/backend/services/llm.py`)**:
   - Updated `SYSTEM_PROMPT` to explicitly instruct the LLM:
     - To speak concisely and naturally in complete sentences.
     - NEVER use emojis (`😊`, `🚀`, etc.) or ASCII emoticons (`:)`, `xD`, `<3`, etc.).
     - NEVER use markdown formatting like asterisks (`*`, `**`), underscores (`_`), hash headers (`#`), backticks (`` ` ``), bullet lists, or tables.
     - NEVER output unreadable unicode characters, decorative symbols, or ASCII art.
     - Avoid bulleted or numbered lists; use natural spoken transitions.
     - Avoid code snippets, URLs, and complex syntax unless explicitly requested.

2. **Robust TTS Text Sanitizer (`apps/backend/services/tts.py`)**:
   - Added `sanitize_for_tts(text: str) -> str` which strips:
     - Markdown links (`[text](url)` -> `text`), images (`![alt](url)` -> `""`), and code fences/backticks.
     - Markdown headers, blockquotes, and bullet markers at start of lines.
     - Kaomojis (e.g. `¯\_(ツ)_/¯`, `ಠ_ಠ`, `(^_^)`) and ASCII emoticons (e.g. `:)`, `:-)`, `xD`, `<3`).
     - Bold/italic/strikethrough markers, standalone asterisks, tildes, hashtags, underscores, pipes, and backslashes.
     - Unicode emojis (SMP `0x1F000+`), Dingbats, miscellaneous symbols, bullet glyphs (`•`, `★`, `✓`), and format/invisible characters.
     - Normalized punctuation and collapsed whitespace.
   - Integrated `sanitize_for_tts` directly into `text_to_wav_bytes`, `synthesize_sentence_wav`, and `stream_tts_pcm`.

3. **Server Consistency & Stream Validation (`apps/backend/server.py`)**:
   - Standardized `SYSTEM_PROMPT` usage across REST `/api/chat` and WebSocket `/ws/chat`.
   - Updated WebSocket sentence boundary streaming to sanitize sentences and skip empty payloads before sending `audio_sentence` events.
   - Handled `/api/tts` to return empty audio data gracefully when input text contains no speakable characters after sanitization.

---

## ✅ Verification
- Automated test script verified that:
  - `SYSTEM_PROMPT` contains all required negative constraints.
  - `sanitize_for_tts` properly cleans markdown, emojis, asterisks, bullet points, emoticons, kaomojis, links, and symbols across test cases.
  - Piper TTS synthesizes audio cleanly without verbalizing symbols or errors, and returns empty bytes for pure-emoji/symbol inputs.
