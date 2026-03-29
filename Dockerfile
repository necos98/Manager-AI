# ── Stage 1: Build frontend ──────────────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + static frontend ───────────────────────
FROM python:3.12-slim

WORKDIR /app

# System deps + Node.js (for Claude Code CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Python deps (exclude heavy ML libs)
COPY backend/requirements.txt /tmp/requirements.txt
RUN grep -v -E "sentence-transformers|pypdf" /tmp/requirements.txt > /tmp/req-docker.txt \
    && pip install --no-cache-dir -r /tmp/req-docker.txt \
    && rm /tmp/requirements.txt /tmp/req-docker.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build /build/dist ./frontend/dist

# Copy project-level files
COPY manager.json ./
COPY .env.example ./.env.example
COPY claude_resources/ ./claude_resources/

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create non-root user matching host UID/GID for Claude Code compatibility
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd -g ${USER_GID} appuser \
    && useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash appuser

# Data dir (will be mounted as volume)
RUN mkdir -p /app/data && chown appuser:appuser /app/data

EXPOSE 8000

USER appuser

ENTRYPOINT ["/docker-entrypoint.sh"]
