"""Configuration management for Voice Chat Backend."""

import argparse
import os
from pathlib import Path
import sys
from pydantic import BaseModel, Field

# Load root .env file into environment variables if present
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Default STT model: sherpa-onnx Parakeet TDT 0.6b v2 (English, INT8) on HuggingFace Hub
PARAKEET_REPO_ID = "csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"


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
        default_factory=lambda: os.getenv("MONGO_URI", ""),
        description="MongoDB connection string",
    )
    mongo_db_name: str = Field(
        default_factory=lambda: os.getenv("MONGO_DB_NAME", "voice_chat"),
        description="MongoDB database name",
    )

    # LLM Settings
    engine: str = Field(
        default_factory=lambda: os.getenv("LLM_ENGINE", ""),
        description="LLM provider: 'lmstudio', 'ollama', 'openai', 'openrouter'",
    )
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", ""),
        description="OpenAI-compatible base URL",
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "not-needed"),
        description="API key for LLM provider",
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", ""),
        description="Target model identifier",
    )
    llm_history_limit: int = Field(
        default=int(os.getenv("LLM_HISTORY_LIMIT", "100")),
        description="Maximum number of past messages to send in LLM prompt context",
    )
    cli_llm_override: bool = Field(
        default=False,
        description="Whether LLM parameters were explicitly passed via CLI flags",
    )

    # STT Settings
    stt_model_name: str = Field(
        default=os.getenv("STT_MODEL_NAME", PARAKEET_REPO_ID),
        description="HuggingFace repo ID of the sherpa-onnx Parakeet TDT STT model",
    )
    stt_num_threads: int = Field(
        default=int(os.getenv("STT_THREADS", str(min(8, os.cpu_count() or 4)))),
        description="CPU threads used by the STT recognizer",
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


def get_settings(argv: list[str] | None = None) -> Settings:
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
        default=None,
        choices=["lmstudio", "ollama", "openai", "openrouter"],
    )
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--mongo-uri", type=str, default=os.getenv("MONGO_URI", None))
    parser.add_argument(
        "--stt-model",
        type=str,
        default=os.getenv("STT_MODEL_NAME", PARAKEET_REPO_ID),
        help="HuggingFace repo ID of the sherpa-onnx Parakeet TDT STT model",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=int(os.getenv("LLM_HISTORY_LIMIT", "100")),
        help="Maximum past messages to send in LLM prompt context",
    )

    raw_argv = argv if argv is not None else sys.argv[1:]
    cli_llm_override = any(
        arg.split("=")[0] in ("--engine", "--model", "--base-url", "--api-key")
        for arg in raw_argv
    )
    args, _ = parser.parse_known_args(raw_argv)

    engine = (args.engine or os.getenv("LLM_ENGINE", "")).lower()
    base_url = args.base_url or os.getenv("LLM_BASE_URL", "")
    model = args.model or os.getenv("LLM_MODEL", "")
    api_key = args.api_key or os.getenv("LLM_API_KEY", "not-needed")
    if engine == "openai" and "api.openai.com" in base_url and api_key == "not-needed":
        print(
            "⚠️  Engine 'openai' targets https://api.openai.com/v1 with no API key. "
            "For a local OpenAI-compatible server, pass --base-url "
            "(e.g. http://127.0.0.1:1234/v1); for real OpenAI, pass --api-key."
        )
    mongo_uri = args.mongo_uri or os.getenv("MONGO_URI", "")
    stt_model_name = args.stt_model or os.getenv("STT_MODEL_NAME", PARAKEET_REPO_ID)

    return Settings(
        host=args.host,
        port=args.port,
        reload=args.reload,
        engine=engine,
        llm_base_url=base_url,
        llm_api_key=api_key,
        llm_model=model,
        llm_history_limit=args.history_limit,
        cli_llm_override=cli_llm_override,
        mongo_uri=mongo_uri,
        stt_model_name=stt_model_name,
    )


settings = get_settings()
