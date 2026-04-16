# Multi-stage Dockerfile for Entropy

# ── Stage 1: Build React dashboard ────────────────────────────────────────
FROM node:20-alpine AS dashboard-builder
WORKDIR /app/dashboard
COPY dashboard/package.json ./
# Install deps (no package-lock.json yet — npm install will create it)
RUN npm install
COPY dashboard/ ./
RUN npm run build

# ── Stage 2: Python application ───────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps: git is required by PyDriller for repo analysis
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure git to allow root ownership (needed in Docker)
RUN git config --global --add safe.directory '*'

# Install Python deps — copy pyproject.toml first for layer caching
COPY pyproject.toml ./

# Stub out the package dir so pip can read project metadata
RUN mkdir -p entropy && touch entropy/__init__.py

RUN pip install --no-cache-dir -e ".[server]"

# Copy full application code (overwrites the stub __init__.py)
COPY entropy/ ./entropy/
COPY entropy.toml.example ./

# Copy built React dashboard
COPY --from=dashboard-builder /app/dashboard/dist ./dashboard/dist

# Expose API port
EXPOSE 8000

# Default: run the API server
CMD ["uvicorn", "entropy.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
