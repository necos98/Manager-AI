# Deployment Guide

**Generated:** 2026-06-07

## Architecture

Manager AI is a desktop-oriented application with no Docker/container deployment. The primary deployment model is local execution.

## Local Deployment

```bash
# Start full stack (backend + frontend)
python start.py
```

This handles:
1. Virtual environment creation/activation
2. Python dependency installation
3. Database migrations (Alembic)
4. Node dependency installation (frontend)
5. Starting backend (uvicorn on :8000)
6. Starting frontend (Vite dev server on :5173)

## Configuration

| File | Purpose |
|------|---------|
| `.env` | Environment variables (DB path, CORS origins, ports) |
| `.env.example` | Template with all config keys |
| `manager.json` | Project ID mapping |
| `data/secret.key` | Auto-generated Fernet encryption key |

## Infrastructure Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Windows 10+ (primary), Linux/macOS (partial) |
| Python | 3.12–3.14 |
| Node.js | Latest LTS |
| Database | SQLite (file-based, no server needed) |
| Terminal | Windows: pywinpty; Linux: built-in pty |
| WSL (optional) | For Linux shell in Windows terminals |

## Production Considerations

- **Single-process only:** `uvicorn --workers 1` due to SQLite write serialization
- **No Redis/Postgres:** Stack uses SQLite + WriteQueue pattern
- **No Docker:** `start.py` is the deployment orchestrator
- **CORS:** Configure `cors_origins` in `.env` if frontend/backend on different hosts
- **Scaling limit:** SQLite practical up to ~1GB data

## CI/CD

No CI/CD pipelines currently configured. No Dockerfile or docker-compose.yml.
