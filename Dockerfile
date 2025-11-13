# Multi-stage Dockerfile for Networking AI Platform
# Optimized for production deployment with minimal image size

# Stage 1: Builder
FROM python:3.11-slim AS builder

LABEL maintainer="Networking AI Team"
LABEL description="Networking AI Platform - Production Build"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt && \
    pip install gunicorn uvicorn[standard]

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    WORKERS=4 \
    PORT=8000 \
    LOG_LEVEL=info \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security with proper home directory
RUN groupadd -r appuser && \
    useradd -r -g appuser -m -d /home/appuser -s /bin/bash appuser && \
    mkdir -p /home/appuser/.cache/huggingface/hub && \
    mkdir -p /home/appuser/.cache/torch && \
    chown -R appuser:appuser /home/appuser && \
    chmod -R 755 /home/appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory and create it
RUN mkdir -p /app && chown appuser:appuser /app
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/uploads && \
    mkdir -p /app/.cache/huggingface/hub && \
    mkdir -p /app/.cache/torch && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Install application in editable mode as appuser
RUN pip install -e .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default command (can be overridden)
CMD ["sh", "-c", "uvicorn networking_ai.api.main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}"]
