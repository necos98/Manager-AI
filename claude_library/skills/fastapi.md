---
name: fastapi
category: tech
description: FastAPI patterns, async SQLAlchemy, Pydantic v2
built_in: true
---
# FastAPI Conventions

## Structure
- Routers are thin: no business logic, only HTTP wiring
- Services hold all business logic, accept AsyncSession
- Pydantic v2 schemas for request/response validation
- Custom exception hierarchy with global handler

## Database
- SQLAlchemy async ORM with `AsyncSession`
- `Mapped` typed columns, never use old-style `Column()`
- Migrations with Alembic

## Testing
- pytest-asyncio with `asyncio_mode = "auto"`
- In-memory SQLite for tests
- httpx `AsyncClient` with `ASGITransport`

## Error Handling
- Raise custom `AppError` subclasses in services
- Global exception handler in FastAPI maps to HTTP responses
- Never catch exceptions in routers
