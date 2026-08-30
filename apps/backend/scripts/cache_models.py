"""Script to pre-cache neural models during Docker build."""

import os
import sys

# Ensure repository root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def cache_all_models():
    print("🚀 Pre-caching neural models for Docker build...")

    # 1. Piper TTS Voice Model
    try:
        from apps.backend.common.model_manager import load_piper_voice_model

        print("📥 Caching Piper TTS voice model...")
        load_piper_voice_model()
        print("✅ Piper TTS voice model cached.")
    except Exception as e:
        print(f"⚠️ Failed to cache Piper TTS voice model: {e}")

    # 2. Moonshine Voice STT Models
    try:
        from moonshine_voice import ModelArch, get_model_for_language

        print("📥 Caching Moonshine STT model (medium-streaming)...")
        get_model_for_language("en", ModelArch.MEDIUM_STREAMING)
        print("✅ Moonshine STT model cached.")
    except Exception as e:
        print(f"⚠️ Failed to cache Moonshine STT model: {e}")

    # 3. FastEmbed RAG Embedding Model
    try:
        from fastembed import TextEmbedding

        print("📥 Caching FastEmbed model (BAAI/bge-small-en-v1.5)...")
        TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        print("✅ FastEmbed model cached.")
    except Exception as e:
        print(f"⚠️ Failed to cache FastEmbed model: {e}")

    print("🎉 Neural models pre-caching finished.")


if __name__ == "__main__":
    cache_all_models()
