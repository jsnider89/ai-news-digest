#!/bin/sh
set -e

# Set defaults if not provided
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}

echo "Starting AI News Digest on ${HOST}:${PORT}"

# Initialize database
python -m app.tasks.prestart

# Start the application
exec uvicorn app.web.main:app --host $HOST --port $PORT
