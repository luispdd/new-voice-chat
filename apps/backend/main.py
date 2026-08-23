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
    print("=" * 60)

    # Check for SSL certs
    ssl_kwargs = {}
    if os.path.exists(settings.ssl_cert) and os.path.exists(settings.ssl_key):
        print(f"🔒 SSL enabled using {settings.ssl_cert} and {settings.ssl_key}")
        ssl_kwargs = {
            "ssl_certfile": settings.ssl_cert,
            "ssl_keyfile": settings.ssl_key,
        }

    uvicorn.run(
        "apps.backend.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
