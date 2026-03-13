# Backend Agent

## Scope
`backend/` — FastAPI routes, services, database, auth

## Context (read before starting)
- `CLAUDE.md` — project overview and standards
- `backend/db/models.py` — database models
- `backend/schemas/` — Pydantic schemas (API contracts)
- `backend/api/router.py` — existing route structure

## Instructions
- Python 3.11+, async everywhere
- Type hints on all functions
- Pydantic models for all request/response bodies
- SQLAlchemy async sessions via `get_db` dependency
- JWT auth via `get_current_user` dependency
- Always validate user ownership before returning data
- Follow existing service pattern (routes → services → DB)

## Conventions
<!-- Add conventions here as we establish them -->
<!-- Example: - All list endpoints support pagination -->
<!-- Example: - Use HTTP 422 for validation errors, 404 for not found -->
