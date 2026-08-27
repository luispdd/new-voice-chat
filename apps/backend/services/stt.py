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
            channels = f.channels
            # Convert multi-channel to mono
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            # Compute stats of original audio
            duration = len(audio) / samplerate
            peak = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
            rms = float(np.sqrt(np.mean(audio**2))) if len(audio) > 0 else 0.0
            print(f"[STT Diagnostics] Format: WAV (soundfile), Samplerate: {samplerate}Hz, Channels: {channels}, Duration: {duration:.3f}s, Peak: {peak:.3f}, RMS: {rms:.3f}")

            # Resample to 16000Hz if needed
            if samplerate != 16000:
                audio_clipped = np.clip(audio, -1.0, 1.0)
                pcm_data = (audio_clipped * 32767.0).astype(np.int16).tobytes()
                audio_seg = AudioSegment(
                    pcm_data,
                    frame_rate=samplerate,
                    sample_width=2,
                    channels=1,
                ).set_frame_rate(16000)
                audio = np.array(audio_seg.get_array_of_samples(), dtype=np.float32) / 32768.0
            return audio
    except Exception as sf_err:
        try:
            # Fallback to PyDub for WebM, MP3, or OGG chunks
            audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
            samplerate = audio_seg.frame_rate
            channels = audio_seg.channels
            audio_seg = audio_seg.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            # Convert 16-bit PCM to float32 (-1.0 to 1.0)
            samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32)
            samples = samples / 32768.0
            
            duration = len(samples) / 16000
            peak = float(np.max(np.abs(samples))) if len(samples) > 0 else 0.0
            rms = float(np.sqrt(np.mean(samples**2))) if len(samples) > 0 else 0.0
            print(f"[STT Diagnostics] Format: Fallback (pydub), Orig Samplerate: {samplerate}Hz, Channels: {channels}, Duration: {duration:.3f}s, Peak: {peak:.3f}, RMS: {rms:.3f}")
            return samples
        except Exception as pydub_err:
            print(f"[STT Diagnostics] Audio conversion failed. sf_err: {sf_err}, pydub_err: {pydub_err}")
            raise


def _split_audio_into_chunks(audio_data: np.ndarray, samplerate: int = 16000, max_chunk_len_s: float = 8.0) -> list[np.ndarray]:
    """
    Split a 1D float32 audio array into chunks of at most max_chunk_len_s.
    Tries to split at silence points (lowest energy) to avoid clipping words.
    """
    total_samples = len(audio_data)
    max_samples = int(max_chunk_len_s * samplerate)
    min_samples = int(0.5 * samplerate) # Minimum chunk of 0.5s to avoid tiny fragments
    
    if total_samples <= max_samples:
        return [audio_data]
        
    chunks = []
    start = 0
    while start < total_samples:
        remaining = total_samples - start
        if remaining <= max_samples:
            if remaining < min_samples and chunks:
                chunks[-1] = np.concatenate([chunks[-1], audio_data[start:]])
            else:
                chunks.append(audio_data[start:])
            break
            
        # Target size is max_samples. Search window for silence: 50% to 95% of max_samples
        search_start = start + int(max_samples * 0.5)
        search_end = start + int(max_samples * 0.95)
        search_end = min(search_end, total_samples - min_samples)
        
        if search_start >= search_end:
            split_idx = start + max_samples
        else:
            search_area = audio_data[search_start:search_end]
            window_size = int(0.1 * samplerate) # 100ms window
            
            if len(search_area) < window_size:
                split_idx = (search_start + search_end) // 2
            else:
                min_energy = float('inf')
                best_offset = 0
                step = int(0.05 * samplerate) # 50ms step
                
                for offset in range(0, len(search_area) - window_size, step):
                    window = search_area[offset:offset + window_size]
                    energy = np.sum(np.abs(window))
                    if energy < min_energy:
                        min_energy = energy
                        best_offset = offset + (window_size // 2)
                        
                split_idx = search_start + best_offset
                
        chunks.append(audio_data[start:split_idx])
        start = split_idx
        
    return chunks


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio bytes into text.

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
    if len(audio_data) > 60 * 16000:  # More than 60 seconds
        print(f"[STT Diagnostics] Audio segment too long: {len(audio_data)} samples ({duration:.3f}s). Truncating to 60s.")
        audio_data = audio_data[:60 * 16000]

    # Split audio into chunks of at most 8.0s to avoid Moonshine ONNX shape limits
    chunks = _split_audio_into_chunks(audio_data, 16000, max_chunk_len_s=8.0)
    print(f"[STT Diagnostics] Split {len(audio_data)/16000:.3f}s audio into {len(chunks)} chunk(s) for transcription.")

    transcriptions = []
    for i, chunk in enumerate(chunks):
        if len(chunk) < 1600:  # Skip tiny fragments
            continue
        try:
            results = moonshine_onnx.transcribe(chunk, model=settings.stt_model_name)
            if isinstance(results, list) and len(results) > 0:
                text = str(results[0]).strip()
            else:
                text = str(results).strip()
            print(f"[STT Diagnostics] Chunk {i+1}/{len(chunks)} ({len(chunk)/16000:.2f}s) decoded: '{text}'")
            if text:
                transcriptions.append(text)
        except Exception as e:
            print(f"[STT Diagnostics] Error transcribing chunk {i+1}: {e}")

    final_text = " ".join(transcriptions).strip()
    print(f"[STT Diagnostics] Final Decoded Text: '{final_text}'")
    return final_text
