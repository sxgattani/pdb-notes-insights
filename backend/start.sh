#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application..."
exec gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
