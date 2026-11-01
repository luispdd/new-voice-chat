"""Speech-to-Text (STT) service utilizing Parakeet TDT 0.6b v2 (sherpa-onnx, CPU, English)."""

import io
import threading
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from apps.backend.common.model_manager import load_parakeet_recognizer
from apps.backend.config import settings

SAMPLE_RATE = 16000
MAX_UTTERANCE_SECONDS = 60

_stt_model = None
_stt_lock = threading.Lock()  # The recognizer is shared by the WebSocket and REST paths


def get_stt_model():
    """Warmup and initialize the Parakeet recognizer singleton."""
    global _stt_model
    if _stt_model is None:
        print(f"📦 Initializing Parakeet STT Model ({settings.stt_model_name})...")
        _stt_model = load_parakeet_recognizer(settings.stt_model_name, settings.stt_num_threads)
        try:
            _decode(_stt_model, np.zeros(SAMPLE_RATE, dtype=np.float32))
        except Exception as e:
            print(f"⚠️ STT warmup info: {e}")
        print(f"✅ Parakeet STT Model ({settings.stt_model_name}) initialized.")
    return _stt_model


def _decode(model, audio: np.ndarray) -> str:
    with _stt_lock:
        stream = model.create_stream()
        stream.accept_waveform(SAMPLE_RATE, audio.astype(np.float32))
        model.decode_stream(stream)
        return " ".join(stream.result.text.split())


def pcm16_to_float32(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Convert little-endian 16-bit mono PCM bytes to a 16 kHz float32 array."""
    usable = len(pcm) - (len(pcm) % 2)
    samples = np.frombuffer(pcm[:usable], dtype="<i2")
    if sample_rate != SAMPLE_RATE and len(samples) > 0:
        seg = AudioSegment(samples.tobytes(), frame_rate=sample_rate, sample_width=2, channels=1)
        samples = np.array(seg.set_frame_rate(SAMPLE_RATE).get_array_of_samples(), dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


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


def transcribe_pcm(audio_data: np.ndarray) -> str:
    """
    Transcribe a 16 kHz mono float32 array into text.

    Applies the 60 s cap and a peak-normalized retry on audible
    speech that decodes to an empty string. Blocking: call from a worker thread
    when running inside the event loop.
    """
    if len(audio_data) > 0:
        audio_data = audio_data - np.mean(audio_data)  # Remove DC offset

    duration = len(audio_data) / SAMPLE_RATE
    if len(audio_data) < 1600:  # Less than 0.1 seconds of audio
        print(f"[STT Diagnostics] Audio segment too short: {len(audio_data)} samples ({duration:.3f}s)")
        return ""

    # Parakeet handles leading/trailing silence well; trimming clipped quiet speech onsets
    if float(np.sqrt(np.mean(audio_data**2))) < 0.002:  # Digital silence: nothing to decode
        print("[STT Diagnostics] Audio is essentially silent; skipping decode.")
        return ""

    max_samples = MAX_UTTERANCE_SECONDS * SAMPLE_RATE
    if len(audio_data) > max_samples:
        print(f"[STT Diagnostics] Audio segment too long: {duration:.3f}s. Truncating to {MAX_UTTERANCE_SECONDS}s.")
        audio_data = audio_data[:max_samples]

    model = get_stt_model()

    try:
        text = _decode(model, audio_data)

        # Retry fallback with peak normalization if result is empty on audible speech
        if not text and float(np.sqrt(np.mean(audio_data**2))) > 0.01:
            peak = float(np.max(np.abs(audio_data)))
            if peak > 0:
                text = _decode(model, (audio_data / peak) * 0.95)

        print(f"[STT Diagnostics] Decoded Text: '{text}'")
        return text
    except Exception as e:
        print(f"[STT Diagnostics] Error transcribing audio: {e}")
        return ""


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio file bytes (WAV, WebM, FLAC, ...) into text.

    Args:
        audio_bytes: In-memory encoded audio file bytes.

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

    return transcribe_pcm(audio_data)
