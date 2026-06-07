# Project Overview — Manager AI

**Generated:** 2026-06-07

## Executive Summary

Manager AI is a full-stack web application for AI-powered project management with Claude Code integration. It provides issue tracking, terminal emulation, real-time event notifications, and an MCP server that exposes tools to Claude Code for autonomous issue processing.

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI 0.115, SQLite + SQLAlchemy 2.0 |
| Frontend | React 19, TypeScript 6, Vite 5, TanStack Router/Query |
| Styling | Tailwind CSS 4, Radix UI |
| AI Integration | FastMCP 1.9 (StreamableHTTP), Claude Code hooks |
| Terminal | Xterm.js + pywinpty (Windows) |
| Build | Vite 5 (frontend), Alembic (DB migrations) |

## Architecture Type

- **Repository:** Monorepo (2 parts)
- **Backend:** Layered (Router → Service → Model/Schema) — Python/FastAPI
- **Frontend:** Feature-based with shared components — React/TypeScript
- **Communication:** REST API + WebSocket + MCP StreamableHTTP

## Key Features

- **Issue Management:** Full lifecycle (New → Reasoning → Planned → Accepted → Finished)
- **AI Pipeline:** Automated issue processing via Claude Code executor + MCP tools
- **Terminal Emulation:** In-browser PTY terminals with WSL support
- **Real-time Events:** WebSocket-based live updates
- **Memory System:** Persistent project memories with vector search (LanceDB)
- **Plugin System:** Extensible catalog with credential management
- **File Management:** Upload, preview, text extraction (PDF/DOCX/XLSX)
- **Multi-project:** Multiple project support with MCP installation

## Repository Structure

```
├── backend/     # FastAPI REST API server
├── frontend/    # React SPA
├── docs/        # Project documentation
├── data/        # SQLite DB + vectors
└── start.py     # Full-stack launcher
```

## Quick Start

```bash
python start.py
```

Starts backend on `:8000` and frontend on `:5173`.

## Documentation Index

See [index.md](./index.md) for full navigation.
