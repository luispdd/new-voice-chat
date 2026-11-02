# Minimal Python 3.13 Production Image with uv
FROM python:3.13-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifests
COPY apps/backend/pyproject.toml apps/backend/uv.lock apps/backend/README.md ./apps/backend/

# Install production dependencies
WORKDIR /app/apps/backend
RUN uv sync --frozen --no-dev

# Pre-cache ONNX models and Piper voice assets in a dedicated build layer
# Copy only model manager and caching script first so code edits don't invalidate the ~900MB model cache
WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
COPY apps/backend/__init__.py ./apps/backend/__init__.py
COPY apps/backend/common ./apps/backend/common
COPY apps/backend/scripts/cache_models.py ./apps/backend/scripts/cache_models.py
RUN uv run --project apps/backend python apps/backend/scripts/cache_models.py

# Copy remaining backend application source code
COPY apps/backend ./apps/backend

# Expose backend port
EXPOSE 8000

# Start server entrypoint
CMD ["uv", "run", "--project", "apps/backend", "python", "apps/backend/main.py"]
