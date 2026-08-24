"""Speech-to-Text (STT) service utilizing Moonshine ONNX."""

import io
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import moonshine_onnx
from apps.backend.config import settings

_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = moonshine_onnx.load_tokenizer()
    return _tokenizer


def get_stt_model():
    """Warmup and initialize tokenizer and Moonshine ONNX model."""
    get_tokenizer()
    dummy = np.zeros(16000, dtype=np.float32)
    try:
        moonshine_onnx.transcribe(dummy, model=settings.stt_model_name)
    except Exception as e:
        print(f"STT warmup info: {e}")
    return True


def audio_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """
    Convert incoming audio bytes (WAV, WebM, MP3, etc.) to 16kHz mono float32 numpy array.
    """
    try:
        # Try direct soundfile read first (fastest for WAV/FLAC)
        with sf.SoundFile(io.BytesIO(audio_bytes)) as f:
            audio = f.read(dtype="float32")
            samplerate = f.samplerate
            # Convert multi-channel to mono
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            # Resample to 16000Hz if needed
            if samplerate != 16000:
                audio_seg = AudioSegment(
                    audio.tobytes(),
                    frame_rate=samplerate,
                    sample_width=4,
                    channels=1,
                ).set_frame_rate(16000)
                audio = np.frombuffer(audio_seg.raw_data, dtype=np.float32)
            return audio
    except Exception:
        # Fallback to PyDub for WebM, MP3, or OGG chunks
        audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
        audio_seg = audio_seg.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        # Convert 16-bit PCM to float32 (-1.0 to 1.0)
        samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32)
        samples = samples / 32768.0
        return samples


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio bytes into text.

    Args:
        audio_bytes: In-memory raw audio bytes from client microphone.

    Returns:
        Transcribed text string.
    """
    if not audio_bytes:
        return ""

    audio_data = audio_bytes_to_float32(audio_bytes)

    if len(audio_data) < 1600:  # Less than 0.1 seconds of audio
        return ""

    try:
        results = moonshine_onnx.transcribe(audio_data, model=settings.stt_model_name)
        if isinstance(results, list) and len(results) > 0:
            return str(results[0]).strip()
        return str(results).strip()
    except Exception as e:
        print(f"Error in Moonshine STT transcription: {e}")
        return ""
