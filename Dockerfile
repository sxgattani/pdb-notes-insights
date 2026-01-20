# Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Production image
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend code
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create directory for persistent data
RUN mkdir -p /data

# Environment variables (defaults, override in fly.toml)
ENV DATABASE_URL=sqlite:////data/pdb_insights.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run with gunicorn for production
CMD ["gunicorn", "app.main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
