# Stage 1: Build Next.js static export
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install --frozen-lockfile
COPY frontend/ .
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS backend-deps
WORKDIR /deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final runtime image
FROM python:3.12-slim
WORKDIR /app

# System libraries needed at runtime (PyMuPDF, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python packages
COPY --from=backend-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-deps /usr/local/bin /usr/local/bin

# App source
COPY backend/ ./backend/
COPY agents/ ./agents/
COPY workflows/ ./workflows/
COPY memory/ ./memory/
COPY tools/ ./tools/
COPY tracking/ ./tracking/
COPY intelligence/ ./intelligence/
COPY graph/ ./graph/
COPY retrieval/ ./retrieval/
COPY pattern_engine/ ./pattern_engine/
COPY research_engineering/ ./research_engineering/
COPY simulation/ ./simulation/
COPY simulations/ ./simulations/
COPY evaluation/ ./evaluation/
COPY ingestion/ ./ingestion/

# Built frontend
COPY --from=frontend-builder /frontend/out ./frontend/out

# Persistent data directory (HF Spaces mounts /data)
RUN mkdir -p /data /app/uploads

ENV PYTHONPATH=/app/backend:/app
ENV USE_SQLITE=true
ENV QDRANT_IN_MEMORY=true
ENV UPLOAD_DIR=/app/uploads

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
