"""Main entrypoint script to launch the FastAPI Voice Chat server."""

import os
import uvicorn
from apps.backend.config import settings


def main():
    print("=" * 60)
    print("🚀 VOICE CHAT BACKEND INITIALIZING")
    print("=" * 60)
    print(f"🏠 Host:            {settings.host}:{settings.port}")
    print(f"🧠 Engine:          {settings.engine.upper()} -> {settings.llm_base_url}")
    print(f"🎯 Model:           {settings.llm_model}")
    print(f"📦 MongoDB:         {settings.mongo_uri}")
    print(f"🎙️ STT Model:       {settings.stt_model_name}")
    print(f"🔊 TTS Voice:       {settings.tts_repo_id}")
    reload_dirs_info = settings.reload_dirs if settings.reload else "N/A"
    print(f"🔄 Auto-Reload:     {settings.reload} (dirs: {reload_dirs_info})")
    print("=" * 60)

    # Check for SSL certs
    has_ssl = os.path.exists(settings.ssl_cert) and os.path.exists(settings.ssl_key)
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None
    if has_ssl:
        print(f"🔒 SSL enabled using {settings.ssl_cert} and {settings.ssl_key}")
        ssl_certfile = settings.ssl_cert
        ssl_keyfile = settings.ssl_key

    uvicorn.run(
        "apps.backend.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        reload_dirs=settings.reload_dirs if settings.reload else None,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
    )


if __name__ == "__main__":
    main()
