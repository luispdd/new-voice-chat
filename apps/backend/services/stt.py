"""Speech-to-Text (STT) service utilizing Moonshine Voice."""

import io
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from moonshine_voice import (
    ModelArch,
    Transcriber,
    get_model_for_language,
    string_to_model_arch,
)
from apps.backend.config import settings

_stt_model: Optional[Transcriber] = None


def resolve_model_arch(model_name: str) -> Tuple[str, ModelArch]:
    """
    Resolve language tag and ModelArch enum from model name string.

    Canonical Moonshine Voice architectures:
      - 'medium-streaming' -> ('en', ModelArch.MEDIUM_STREAMING)
      - 'small-streaming'  -> ('en', ModelArch.SMALL_STREAMING)
      - 'base-streaming'   -> ('en', ModelArch.BASE_STREAMING)
      - 'tiny-streaming'   -> ('en', ModelArch.TINY_STREAMING)
      - 'base'             -> ('en', ModelArch.BASE)
      - 'tiny'             -> ('en', ModelArch.TINY)
    """
    cleaned = model_name.strip().lower()
    if "/" in cleaned:
        cleaned = cleaned.split("/")[-1]

    lang = "en"
    if cleaned in ("small", "small-streaming", "streaming-small", "moonshine-streaming-small"):
        arch = ModelArch.SMALL_STREAMING
    elif cleaned in ("tiny-streaming", "streaming-tiny", "moonshine-streaming-tiny"):
        arch = ModelArch.TINY_STREAMING
    elif cleaned in ("medium", "medium-streaming", "streaming-medium", "moonshine-streaming-medium"):
        arch = ModelArch.MEDIUM_STREAMING
    elif cleaned in ("base-streaming", "streaming-base", "moonshine-streaming-base", "moonshine-streaming"):
        arch = ModelArch.BASE_STREAMING
    elif cleaned in ("base", "moonshine-base"):
        arch = ModelArch.BASE
    elif cleaned in ("tiny", "moonshine-tiny"):
        arch = ModelArch.TINY
    else:
        try:
            arch = string_to_model_arch(cleaned)
        except ValueError:
            print(f"⚠️ Unknown STT model architecture '{model_name}', defaulting to MEDIUM_STREAMING")
            arch = ModelArch.MEDIUM_STREAMING

    return lang, arch


def get_stt_model() -> Transcriber:
    """Warmup and initialize Moonshine Transcriber singleton."""
    global _stt_model
    if _stt_model is None:
        lang, arch = resolve_model_arch(settings.stt_model_name)
        print(f"📦 Initializing Moonshine STT Model ({settings.stt_model_name} -> {arch.name})...")
        model_path, model_arch = get_model_for_language(lang, arch)
        _stt_model = Transcriber(model_path, model_arch)

        # Warmup inference
        dummy = [0.0] * 16000
        try:
            stream = _stt_model.create_stream()
            stream.start()
            stream.add_audio(dummy, 16000)
            stream.stop()
            print(f"✅ Moonshine STT Model ({arch.name}) initialized and warmed up.")
        except Exception as e:
            print(f"⚠️ STT warmup info: {e}")
    return _stt_model


def audio_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """
    Convert incoming audio bytes (WAV, WebM, MP3, etc.) to 16kHz mono float32 numpy array
    using pydub AudioSegment and soundfile fallback.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return np.zeros(0, dtype=np.float32)

    # 1. Primary path: AudioSegment
    try:
        audio_stream = io.BytesIO(audio_bytes)
        audio_seg = AudioSegment.from_file(audio_stream)
        audio_seg = audio_seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        raw_samples = audio_seg.get_array_of_samples()
        audio_np = np.array(raw_samples, dtype=np.float32) / 32768.0
    except Exception as pydub_err:
        # Fallback to soundfile if AudioSegment fails
        try:
            with sf.SoundFile(io.BytesIO(audio_bytes)) as f:
                audio = f.read(dtype="float32")
                samplerate = f.samplerate
                if audio.ndim > 1:
                    audio = np.mean(audio, axis=1)
                if samplerate != 16000:
                    pcm_data = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                    audio_seg = AudioSegment(
                        pcm_data,
                        frame_rate=samplerate,
                        sample_width=2,
                        channels=1,
                    ).set_frame_rate(16000)
                    audio_np = np.array(audio_seg.get_array_of_samples(), dtype=np.float32) / 32768.0
                else:
                    audio_np = audio
        except Exception as sf_err:
            print(f"[STT Diagnostics] Audio conversion failed. pydub_err: {pydub_err}, sf_err: {sf_err}")
            raise

    # Remove DC offset
    if len(audio_np) > 0:
        audio_np = audio_np - np.mean(audio_np)

    duration = len(audio_np) / 16000
    peak = float(np.max(np.abs(audio_np))) if len(audio_np) > 0 else 0.0
    rms = float(np.sqrt(np.mean(audio_np**2))) if len(audio_np) > 0 else 0.0
    print(f"[STT Diagnostics] Audio: 16000Hz mono, Duration: {duration:.3f}s, Peak: {peak:.3f}, RMS: {rms:.3f}")

    return audio_np


def trim_silence(
    audio: np.ndarray,
    samplerate: int = 16000,
    frame_duration_ms: int = 30,
    padding_ms: int = 250,
) -> np.ndarray:
    """
    Trim extended leading and trailing silence from audio to prevent decoder
    early-termination on long leading pauses.
    """
    if len(audio) == 0:
        return audio

    frame_size = int(samplerate * frame_duration_ms / 1000)
    padding_samples = int(samplerate * padding_ms / 1000)

    num_frames = len(audio) // frame_size
    if num_frames == 0:
        return audio

    frames = audio[:num_frames * frame_size].reshape(num_frames, frame_size)
    frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))

    max_rms = np.max(frame_rms)
    if max_rms < 0.005:  # Audio is essentially pure silence
        return audio

    threshold = max(0.008, max_rms * 0.05)
    active_frames = np.where(frame_rms > threshold)[0]
    if len(active_frames) == 0:
        return audio

    start_idx = max(0, active_frames[0] * frame_size - padding_samples)
    end_idx = min(len(audio), (active_frames[-1] + 1) * frame_size + padding_samples)

    return audio[start_idx:end_idx]


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio bytes into text using Moonshine STT model.

    Args:
        audio_bytes: In-memory raw audio bytes from client microphone.

    Returns:
        Transcribed text string.
    """
    if not audio_bytes:
        print("[STT Diagnostics] Empty audio bytes received.")
        return ""

    try:
        audio_data = audio_bytes_to_float32(audio_bytes)
    except Exception as e:
        print(f"[STT Diagnostics] Failed to decode audio bytes: {e}")
        return ""

    duration = len(audio_data) / 16000
    if len(audio_data) < 1600:  # Less than 0.1 seconds of audio
        print(f"[STT Diagnostics] Audio segment too short: {len(audio_data)} samples ({duration:.3f}s)")
        return ""

    # Trim leading/trailing silence
    trimmed_audio = trim_silence(audio_data)
    trimmed_duration = len(trimmed_audio) / 16000
    if len(trimmed_audio) < 1600:
        print(f"[STT Diagnostics] Audio only contains silence: {duration:.3f}s -> {trimmed_duration:.3f}s")
        return ""

    if trimmed_duration < duration:
        print(f"[STT Diagnostics] Trimmed silence: {duration:.3f}s -> {trimmed_duration:.3f}s")

    if len(trimmed_audio) > 60 * 16000:  # More than 60 seconds
        print(f"[STT Diagnostics] Audio segment too long: {len(trimmed_audio)} samples ({trimmed_duration:.3f}s). Truncating to 60s.")
        trimmed_audio = trimmed_audio[:60 * 16000]

    model = get_stt_model()

    # Direct transcription of speech sequence
    try:
        stream = model.create_stream()
        stream.start()
        stream.add_audio(trimmed_audio.tolist(), 16000)
        transcript = stream.stop()
        text = " ".join(line.text for line in transcript.lines).strip()

        # Retry fallback with peak normalization if result is empty on audible speech
        if not text and float(np.sqrt(np.mean(trimmed_audio**2))) > 0.01:
            peak = float(np.max(np.abs(trimmed_audio)))
            if peak > 0:
                normalized_audio = (trimmed_audio / peak) * 0.95
                retry_stream = model.create_stream()
                retry_stream.start()
                retry_stream.add_audio(normalized_audio.tolist(), 16000)
                retry_transcript = retry_stream.stop()
                text = " ".join(line.text for line in retry_transcript.lines).strip()

        print(f"[STT Diagnostics] Decoded Text: '{text}'")
        return text
    except Exception as e:
        print(f"[STT Diagnostics] Error transcribing audio: {e}")
        return ""
