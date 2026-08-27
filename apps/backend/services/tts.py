"""Text-to-Speech (TTS) service using Piper TTS and HF Hub Model Manager."""

import io
import re
import unicodedata
import wave
from typing import AsyncGenerator, Generator
from piper.voice import PiperVoice
from apps.backend.common.model_manager import load_piper_voice_model
from apps.backend.config import settings

_voice: PiperVoice | None = None

# Known ASCII emoticons to remove from voice synthesis
RAW_EMOTICONS = [
    ":-)", ":)", ":-(", ":(", ":-D", ":D", ":-d", ":d",
    ":-P", ":P", ":-p", ":p", ";-)", ";)", ";-D", ";D",
    ";-P", ";P", ";-p", ";p", ":-O", ":O", ":-o", ":o",
    ":-/", ":/", r":-\\", r":\\", ":-|", ":|", ":-3", ":3",
    ":-$", ":$", ":'(", ":')", "(:", "(-:", "):", ")-:",
    ";-d", ";d", "=)", "=(", "=D", "=P", "=p",
    "^_^", "^-^", "^^", "-_-", ">_<", ">.<", "-_-\"", ";_;", "T_T", "T.T", "Q_Q",
    "o_O", "O_o", "o.O", "O.o",
]

RAW_EMOTICONS_SORTED = sorted(RAW_EMOTICONS, key=len, reverse=True)

EMOTICON_REGEX = re.compile(
    r"(?<!\S)(?:" + "|".join(re.escape(e) for e in RAW_EMOTICONS_SORTED) + r")(?!\S)",
    flags=re.IGNORECASE,
)

WORDS_EMOTICONS = re.compile(r"(?i)\b(?:xD|XD|xd|rawr)\b")
HEART_EMOTICONS = re.compile(r"(?:<3|</3)")
SHRUG_REGEX = re.compile(r"¯\\?_[\(（][^()（）]*?[\)）]_/¯")
PAREN_KAOMOJI = re.compile(r"[\(（][^a-zA-Z0-9\s]{2,}[\)）]")

# Special symbols, decorative markers, bullets, and syntax delimiters to strip
BULLET_AND_SYMBOLS = re.compile(r"[•◦▪▫◆◇※★☆✓✔✕✖♪♫►◄▲▼→←↑↓—–|\\<>\[\]{}~#*`^/]")


def sanitize_for_tts(text: str) -> str:
    """
    Sanitize text before sending to Piper TTS:
    - Strips markdown formatting, links, images, headers, blockquotes, bullets.
    - Strips unicode emojis, pictographs, symbols, and unreadable characters.
    - Strips ASCII emoticons, kaomojis, and slang tokens.
    - Normalizes punctuation and whitespace so TTS never vocalizes asterisks or emojis.
    """
    if not text:
        return ""

    # 1. Strip markdown images and links: ![alt](url) -> '', [text](url) -> text
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cleaned)

    # 2. Strip code block markers and inline code markers
    cleaned = re.sub(r"```(?:\w+)?\n?([\s\S]*?)```", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = cleaned.replace("`", "")

    # 3. Strip headers, blockquotes, lists at start of lines
    cleaned = re.sub(r"(?m)^[ \t]*#+\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*>\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*[-*+]\s+", "", cleaned)

    # 4. Remove shrugs, kaomojis, words/heart emoticons BEFORE splitting underscores
    cleaned = SHRUG_REGEX.sub("", cleaned)
    cleaned = PAREN_KAOMOJI.sub("", cleaned)
    cleaned = WORDS_EMOTICONS.sub("", cleaned)
    cleaned = HEART_EMOTICONS.sub("", cleaned)
    cleaned = EMOTICON_REGEX.sub("", cleaned)

    # 5. Strip markdown formatting: bold, italic, strikethrough
    cleaned = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", cleaned)
    cleaned = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", cleaned)
    cleaned = re.sub(r"~~([^~]+)~~", r"\1", cleaned)
    cleaned = cleaned.replace("_", " ")

    # 6. Remove symbols, bullets, asterisks, brackets, backslashes, etc.
    cleaned = BULLET_AND_SYMBOLS.sub(" ", cleaned)

    # 7. Strip unreadable Unicode characters (Emojis, Pictographs, Dingbats, Modifier/Format symbols)
    chars = []
    for char in cleaned:
        cat = unicodedata.category(char)
        code = ord(char)
        # Skip unicode emojis & surrogate/SMP symbols (0x1F000 and above)
        if code >= 0x1F000 or (0x2600 <= code <= 0x27BF) or (0x2300 <= code <= 0x23FF):
            continue
        # Skip symbol categories & format/invisible
        if cat in ("So", "Sk", "Cf", "Co", "Cn"):
            continue
        # Drop special characters used purely as kaomojis (e.g. Kannada/Japanese kaomoji chars)
        if char in "ಠツ益ノシ":
            continue
        chars.append(char)
    cleaned = "".join(chars)

    # 8. Clean up empty parentheses/brackets that might remain: e.g. "()", "( )"
    cleaned = re.sub(r"\(\s*\)", " ", cleaned)

    # 9. Normalize whitespace and punctuation
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"([!?]){2,}", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\.)\.{2}(?!\.)", ".", cleaned)
    cleaned = re.sub(r"\.{4,}", "...", cleaned)

    return cleaned.strip()


def get_voice_model() -> PiperVoice:
    """Lazily load and cache Piper voice model via HF Hub."""
    global _voice
    if _voice is None:
        _voice = load_piper_voice_model(
            repo_id=settings.tts_repo_id,
            model_file=settings.tts_model_file,
            config_file=settings.tts_config_file,
        )
        print("✅ Piper TTS Voice Model initialized and ready.")
    return _voice


def text_to_wav_bytes(text: str) -> bytes:
    """
    Synthesize complete text into WAV audio bytes after sanitizing unreadable tokens.
    """
    cleaned = sanitize_for_tts(text)
    if not cleaned:
        return b""

    voice = get_voice_model()
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(cleaned, wav_file)

    buf.seek(0)
    return buf.read()


def split_into_sentences(text_stream: str) -> list[str]:
    """
    Split a stream of text into complete sentences along punctuation boundaries.
    """
    # Regex split on sentence terminators (. ! ? \n) followed by space or end
    sentences = re.split(r"(?<=[.!?\n])\s+", text_stream)
    return [s.strip() for s in sentences if s.strip()]


def synthesize_sentence_wav(sentence: str) -> bytes:
    """
    Synthesize a single sentence into WAV bytes with proper headers.
    """
    return text_to_wav_bytes(sentence)


def stream_tts_pcm(text: str) -> Generator[bytes, None, None]:
    """
    Synthesize text and yield raw 16-bit PCM audio bytes chunk by chunk.
    """
    cleaned = sanitize_for_tts(text)
    if not cleaned:
        return

    voice = get_voice_model()
    for chunk in voice.synthesize(cleaned):
        if chunk.audio_int16_bytes:
            yield chunk.audio_int16_bytes
