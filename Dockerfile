# --- Frontend build stage ----------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --frozen-lockfile
COPY frontend/ ./
RUN npm run build

# --- Python runtime stage ----------------------------------------------------
FROM python:3.11-slim AS runtime

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY data ./data

# Copy built frontend into FastAPI static directory
COPY --from=frontend-builder /frontend/dist ./app/web/static

# Copy application files
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create data directory and set permissions
RUN mkdir -p /data && chown -R appuser:appuser /app /data

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/status/health || exit 1

# Switch to non-root user
USER appuser

EXPOSE 8002
VOLUME ["/data"]
ENTRYPOINT ["/app/entrypoint.sh"]
