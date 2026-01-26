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
COPY backend/start.sh ./
RUN chmod +x start.sh

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create directory for persistent data
RUN mkdir -p /data

# Environment variables (defaults, override in fly.toml)
ENV DATABASE_URL=sqlite:////data/pdb_insights.db
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run migrations and start app
CMD ["./start.sh"]
