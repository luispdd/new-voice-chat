"""Configuration management for Voice Chat Backend."""

import argparse
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Server settings
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload on code changes")
    reload_dirs: list[str] = Field(
        default=["apps/backend"],
        description="Directories to monitor for auto-reload",
    )
    ssl_cert: str = Field(default="cert.pem", description="Path to SSL cert")
    ssl_key: str = Field(default="key.pem", description="Path to SSL private key")
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )

    # Database settings
    mongo_uri: str = Field(
        default=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        description="MongoDB connection string",
    )
    mongo_db_name: str = Field(
        default=os.getenv("MONGO_DB_NAME", "voice_chat"),
        description="MongoDB database name",
    )

    # LLM Settings
    engine: str = Field(
        default=os.getenv("LLM_ENGINE", "lmstudio"),
        description="LLM provider: 'lmstudio', 'ollama', 'openai', 'openrouter'",
    )
    llm_base_url: str = Field(
        default=os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
        description="OpenAI-compatible base URL",
    )
    llm_api_key: str = Field(
        default=os.getenv("LLM_API_KEY", "not-needed"),
        description="API key for LLM provider",
    )
    llm_model: str = Field(
        default=os.getenv("LLM_MODEL", "google/gemma-3-4b-it-qat"),
        description="Target model identifier",
    )

    # STT Settings
    stt_model_name: str = Field(
        default="moonshine/base",
        description="Moonshine ONNX model variant (moonshine/base or moonshine/tiny)",
    )

    # TTS Settings
    tts_repo_id: str = Field(
        default="rhasspy/piper-voices",
        description="HuggingFace repository ID for Piper voices",
    )
    tts_model_file: str = Field(
        default="en/en_GB/cori/high/en_GB-cori-high.onnx",
        description="Model ONNX file in repository",
    )
    tts_config_file: str = Field(
        default="en/en_GB/cori/high/en_GB-cori-high.onnx.json",
        description="Model JSON config file in repository",
    )


def get_settings() -> Settings:
    parser = argparse.ArgumentParser(description="Voice Chat Backend Server")
    parser.add_argument("--host", type=str, default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("RELOAD", "false").lower() in ("true", "1", "yes"),
        help="Enable auto-reload on code changes (scoped to apps/backend)",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default=os.getenv("LLM_ENGINE", "lmstudio"),
        choices=["lmstudio", "ollama", "openai", "openrouter"],
    )
    parser.add_argument("--model", type=str, default=os.getenv("LLM_MODEL", None))
    parser.add_argument("--base-url", type=str, default=os.getenv("LLM_BASE_URL", None))
    parser.add_argument("--api-key", type=str, default=os.getenv("LLM_API_KEY", None))
    parser.add_argument("--mongo-uri", type=str, default=os.getenv("MONGO_URI", None))

    args, _ = parser.parse_known_args()

    engine = args.engine.lower()
    base_url = args.base_url
    if not base_url:
        if engine == "ollama":
            base_url = "http://127.0.0.1:11434/v1"
        elif engine == "openai":
            base_url = "https://api.openai.com/v1"
        elif engine == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        else:  # lmstudio default
            base_url = "http://127.0.0.1:1234/v1"

    model = args.model
    if not model:
        if engine == "ollama":
            model = "llama3"
        elif engine == "openai":
            model = "gpt-4o-mini"
        elif engine == "openrouter":
            model = "meta-llama/llama-3.3-70b-instruct"
        else:  # lmstudio default
            model = "google/gemma-3-4b-it-qat"

    api_key = args.api_key or os.getenv("LLM_API_KEY", "not-needed")
    mongo_uri = args.mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")

    return Settings(
        host=args.host,
        port=args.port,
        reload=args.reload,
        engine=engine,
        llm_base_url=base_url,
        llm_api_key=api_key,
        llm_model=model,
        mongo_uri=mongo_uri,
    )


settings = get_settings()
