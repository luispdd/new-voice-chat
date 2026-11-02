"""
Piper TTS Model Management.

Handles downloading and caching Piper voice models from HuggingFace Hub.
Uses ONNX Runtime for inference.

Usage:
    from apps.backend.common.model_manager import load_piper_voice_model

    voice_model = load_piper_voice_model()
"""

import json
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from piper.config import PiperConfig
from piper.voice import PiperVoice

# Centralized Piper voice model repository settings
HF_REPO_ID = "rhasspy/piper-voices"
HF_MODEL_FILE = "en/en_GB/cori/high/en_GB-cori-high.onnx"
HF_CONFIG_FILE = "en/en_GB/cori/high/en_GB-cori-high.onnx.json"


def load_piper_voice_model(
    repo_id: str = HF_REPO_ID,
    model_file: str = HF_MODEL_FILE,
    config_file: str = HF_CONFIG_FILE,
) -> PiperVoice:
    """
    Load Piper TTS voice model from HuggingFace Hub.

    Downloads to ~/.cache/huggingface/ if not already cached.
    Initializes ONNX Runtime session with optimized thread settings.

    Args:
        repo_id: HuggingFace repository ID
        model_file: ONNX model file path in repo
        config_file: JSON config file path in repo

    Returns:
        Configured PiperVoice instance ready for synthesis
    """
    print(f"📦 Verifying/Downloading Piper Voice Model ({repo_id}:{model_file})...")

    # Downloads to HF cache directory and returns absolute local paths
    model_path = hf_hub_download(repo_id=repo_id, filename=model_file)
    config_path = hf_hub_download(repo_id=repo_id, filename=config_file)

    # Configure ONNX session with thread limits for CPU efficiency
    sess_opt = ort.SessionOptions()
    sess_opt.intra_op_num_threads = 2
    sess_opt.inter_op_num_threads = 2
    session = ort.InferenceSession(
        model_path, sess_opt, providers=["CPUExecutionProvider"]
    )

    # Load and parse config
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    return PiperVoice(config=PiperConfig.from_dict(config_dict), session=session)


# Parakeet TDT 0.6b v2 (English, INT8) STT model repository settings
PARAKEET_REPO_ID = "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
PARAKEET_FILES = ("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt")


def load_parakeet_recognizer(repo_id: str = PARAKEET_REPO_ID, num_threads: int = 4):
    """
    Load the Parakeet TDT STT recognizer (sherpa-onnx) from HuggingFace Hub.

    Downloads to ~/.cache/huggingface/ if not already cached.

    Returns:
        A `sherpa_onnx.OfflineRecognizer` ready for decoding 16 kHz mono float32 audio.
    """
    import sherpa_onnx  # pylint: disable=import-outside-toplevel

    print(f"📦 Verifying/Downloading Parakeet STT Model ({repo_id})...")
    paths = {name: hf_hub_download(repo_id=repo_id, filename=name) for name in PARAKEET_FILES}

    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=paths["encoder.int8.onnx"],
        decoder=paths["decoder.int8.onnx"],
        joiner=paths["joiner.int8.onnx"],
        tokens=paths["tokens.txt"],
        num_threads=num_threads,
        provider="cpu",
        model_type="nemo_transducer",
    )
