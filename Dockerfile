# Enterprise AI Video Production Platform - Dockerfile
# Multi-stage build for optimized image size

# =============================================================================
# Stage 1: Base
# =============================================================================
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# =============================================================================
# Stage 2: Dependencies
# =============================================================================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Build
# =============================================================================
FROM dependencies as build

# Copy application code
COPY . .

# Run tests (optional)
# RUN pytest tests/

# =============================================================================
# Stage 4: Production
# =============================================================================
FROM base as production

# Create non-root user
RUN groupadd -r avp && useradd -r -g avp avp

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application code
COPY --chown=avp:avp ./app ./app
COPY --chown=avp:avp ./requirements.txt ./

# Create necessary directories
RUN mkdir -p /app/storage/uploads /app/storage/output /app/logs \
    && chown -R avp:avp /app

# Switch to non-root user
USER avp

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "4"]
