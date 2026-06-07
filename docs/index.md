# Project Documentation Index — Manager AI

_Generated: 2026-06-07_

## Project Overview

- **Type:** Monorepo with 2 parts
- **Primary Language:** Python (backend) + TypeScript (frontend)
- **Architecture:** Layered (backend) + Feature-based (frontend)

## Quick Reference

### Backend API

- **Type:** Backend
- **Tech Stack:** Python 3.12+, FastAPI 0.115, SQLAlchemy 2.0, SQLite, Pydantic v2
- **Root:** `backend/`
- **Entry Point:** `backend/app/main.py`

### Frontend Web

- **Type:** Web
- **Tech Stack:** React 19, TypeScript 6, Vite 5, TanStack Router/Query, Tailwind 4
- **Root:** `frontend/`
- **Entry Point:** `frontend/src/main.jsx`

## Generated Documentation

### Core Documents

- [Project Overview](./project-overview.md) — Executive summary and quick start
- [Architecture — Backend](./architecture-backend.md) — Layered backend architecture
- [Architecture — Frontend](./architecture-frontend.md) — Feature-based frontend architecture
- [Source Tree Analysis](./source-tree-analysis.md) — Annotated directory structure

### API & Data

- [API Contracts — Backend](./api-contracts-backend.md) — 67+ REST endpoints
- [API Contracts — Frontend](./api-contracts-frontend.md) — Frontend API client patterns
- [Data Models — Backend](./data-models-backend.md) — 24 database tables
- [Data Models — Frontend](./data-models-frontend.md) — TypeScript type shapes

### Components & UI

- [Component Inventory — Frontend](./component-inventory-frontend.md) — 18 UI primitives + feature modules

### Development

- [Development Guide — Backend](./development-guide-backend.md) — Python backend setup
- [Development Guide — Frontend](./development-guide-frontend.md) — React frontend setup
- [Deployment Guide](./deployment-guide.md) — Local deployment instructions

### Integration

- [Integration Architecture](./integration-architecture.md) — Cross-component communication

## Existing Documentation

- [Agent Pipeline Architecture](./agent-pipeline-architecture.md) — AI agent pipeline design
- [WSL Setup Guide](./wsl-setup.md) — Windows WSL configuration
- [Terminale Avanzato (ITA)](./fase-6-terminale-avanzato.md) — Advanced terminal features
- [Galleria Immagini (ITA)](./fase-7-galleria-immagini.md) — Image gallery features
- [Plugin Documentation](./plugins/README.md) — Plugin system guide
- [Adding a Catalog Plugin](./plugins/adding-a-catalog-plugin.md) — Plugin development guide
- [Plugin Configuration](./plugins/configuration.md) — Plugin configuration reference
- [Historical Specs & Plans](./superpowers/) — ~60 design documents from development history

## Getting Started

### Quick Start
```bash
python start.py
```

### Individual Services
```bash
# Backend
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm run dev
```

### Testing
```bash
cd backend && python -m pytest
```

### Key Links
- **Backend API:** http://localhost:8000/docs (Swagger UI)
- **Frontend App:** http://localhost:5173
- **MCP Server:** http://localhost:8000/mcp
