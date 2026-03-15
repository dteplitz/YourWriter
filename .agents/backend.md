# Backend Agent

## Scope
`backend/` — FastAPI routes, services, database, auth

## Context (read before starting)
- `backend/db/models.py` — database models
- `backend/schemas/` — Pydantic schemas (API contracts)
- `backend/api/router.py` — existing route structure
- `backend/services/` — service layer (put business logic here, not in routes)

## Stack
Python 3.11+, FastAPI, uvicorn, SQLAlchemy async + aiosqlite, Pydantic v2, JWT auth.

## Service Pattern
Routes → Services → DB. Business logic never goes in routes directly.
```python
# route
@router.get("/writers/{id}")
async def get_writer(id: int, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    return await writer_service.get_writer(db, id, user.id)

# service
async def get_writer(db: AsyncSession, writer_id: int, user_id: int) -> Writer:
    writer = await db.get(Writer, writer_id)
    if not writer or writer.user_id != user_id:
        raise HTTPException(404)
    return writer
```

## Auth Pattern
```python
from backend.api.deps import get_current_user
# Always validate user ownership before returning data
```

## HTTP Errors
- `422` — validation errors (Pydantic handles automatically)
- `404` — resource not found
- `401` — unauthenticated (handled by get_current_user)
- `403` — forbidden (wrong user)

## SQLite / DB Sessions — CRÍTICO
- **Nunca** mantener una sesión de DB abierta durante LLM calls o streaming — SQLite serializa writes y bloquea todo con "database is locked"
- Los endpoints de streaming **NO usan** `Depends(get_db)` — manejar sesiones manualmente con `async with async_session() as db`
- Patrón: abrir sesión → escribir → commit → cerrar (short-lived)
- `stream_writer_agent()` no recibe `db` como parámetro — carga historial en su propia sesión corta
- Engine configurado con `NullPool` + WAL mode + `busy_timeout=5000` en `backend/db/database.py`

## Server Restart
- **La app la corre Damian.** No iniciar el backend vos salvo que sea absolutamente necesario.
- Si necesitás correrlo: `bash dev.sh` — mata procesos zombie, limpia lock files, arranca limpio
- Después de cualquier cambio, verificar con `curl` antes de decirle a Damian que pruebe en UI
- Nunca asumir que `--reload` levantó los cambios — verificar con una llamada a la API

## Git / Process
- Trabajar en feature branch, nunca commitear directo a `main`
- Branch naming: `feature/<area>-<description>`
- Un cambio lógico por commit, mensaje imperativo
- Type hints en todas las funciones, async donde corresponda
