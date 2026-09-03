# ==============================================================================
# SatQuery AI — Backend Dockerfile
# Production-ready Python 3.11 container for FastAPI, Geospatial & ML Inference
# Built with root context: docker build -f backend/Dockerfile .
# ==============================================================================
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install essential system packages, imaging, and math libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python package dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create application directories for mounts and runtime persistence
RUN mkdir -p /app/backend /app/configs /app/checkpoints /app/results /app/datasets

# Copy application source code and configurations
COPY backend/app /app/backend/app
COPY configs /app/configs
COPY alembic.ini /app/alembic.ini

# Expose FastAPI server port
EXPOSE 8000

# Native healthcheck using FastAPI /api/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production startup command using full package module path
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
