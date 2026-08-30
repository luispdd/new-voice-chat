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

# Copy backend application source code
WORKDIR /app
COPY apps/backend ./apps/backend

# Pre-cache ONNX models and Piper voice assets in build layer
ENV PYTHONPATH=/app
RUN uv run --project apps/backend python apps/backend/scripts/cache_models.py

# Expose backend port
EXPOSE 8000

# Start server entrypoint
CMD ["uv", "run", "--project", "apps/backend", "python", "apps/backend/main.py"]
