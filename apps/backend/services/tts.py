"""Text-to-Speech (TTS) service using Piper TTS and HF Hub Model Manager."""

import io
import re
import wave
from typing import AsyncGenerator, Generator
from piper.voice import PiperVoice
from apps.backend.common.model_manager import load_piper_voice_model
from apps.backend.config import settings

_voice: PiperVoice | None = None


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
    Synthesize complete text into WAV audio bytes.
    """
    if not text.strip():
        return b""

    voice = get_voice_model()
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(text.strip(), wav_file)

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
    if not text.strip():
        return

    voice = get_voice_model()
    for chunk in voice.synthesize(text.strip()):
        if chunk.audio_int16_bytes:
            yield chunk.audio_int16_bytes
