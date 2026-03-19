# Sprint 5.5 — Deploy

*Plataforma elegida: **Railway***
*Enfoque: monorepo, un solo servicio (backend sirve el frontend como static files)*

---

## Etapas

### Etapa 1 — Publicar la app (front + back en Railway) ✅ COMPLETA (2026-03-18)

**URL producción:** `https://yourwriter-production.up.railway.app`

Objetivo: la app accesible en una URL pública. Un solo servicio Railway que sirve tanto la API como el frontend buildeado. Ambiente local también dockerizado para paridad con prod.

**Qué construimos (estado final real):**

1. **`backend/config.py`** — settings centralizadas con `pydantic-settings`:
   - `database_url` (default: SQLite local), `jwt_secret_key`, `cors_origins`, `anthropic_api_key`, `environment`
   - `@property is_production` — controla el SPA routing en main.py

2. **`backend/main.py`** — CORS desde config. SPA routing:
   ```python
   # NO usar StaticFiles(html=True) — no sirve index.html para rutas arbitrarias de React Router
   # En su lugar: mount /assets estático + catch-all route
   if settings.is_production:
       app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
       @app.get("/{full_path:path}")
       async def serve_spa(full_path: str) -> FileResponse:
           return FileResponse("frontend/dist/index.html")
   ```

3. **`backend/db/database.py`** — `DATABASE_URL` desde env/config con normalización:
   - `postgres://` → `postgresql+asyncpg://` (Railway usa el formato corto)
   - `postgresql://` → `postgresql+asyncpg://`
   - WAL event listener condicional (`if "sqlite" in DATABASE_URL`)
   - Debug logging al stderr para diagnóstico en prod

4. **`backend/auth/auth.py`** — `SECRET_KEY` desde `settings.jwt_secret_key`

5. **`frontend/.env.production`** — `VITE_API_URL=/api`

6. **`Dockerfile`** — 4 stages:
   - `dev-backend`: python + deps + uvicorn --reload (para docker compose local)
   - `dev-frontend`: node + npm ci (para docker compose local con HMR)
   - `frontend-builder`: npm ci + npm run build → genera `frontend/dist/`
   - `production`: python + deps + backend + agents + frontend/dist (para Railway)
   - CMD en shell form: `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}` (shell expansion)

7. **`docker-compose.yml`** — ambiente local Docker:
   - `backend` service: target `dev-backend`, ports 8001, volume mount source, hot reload
   - `frontend` service: target `dev-frontend`, ports 3000, volume mount con node_modules named volume
   - `.env` en backend para vars locales

8. **`railway.toml`** — `builder = "DOCKERFILE"`, healthcheck `/health` timeout 120s, NO startCommand (CMD del Dockerfile)

9. **`requirements.txt`** — `asyncpg>=0.30.0`, `pydantic-settings>=2.0.0`, `bcrypt>=3.1.0,<4.0.0`, `httpx`, `pytest`, `pytest-asyncio`

10. **`frontend/vite.config.ts`** — simplificado (solo vite, sin config de test)

11. **`frontend/vitest.config.ts`** — separado (usa `vitest/config` para evitar conflicto de tipos)

12. **`dev.sh`** — actualizado: `docker compose up --build`

**Variables de entorno en Railway (las que Damian seteó):**

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | `postgresql://...` (Railway lo genera al agregar PostgreSQL service) |
| `JWT_SECRET_KEY` | string random seguro |
| `ANTHROPIC_API_KEY` | API key de Anthropic (con comillas simples si tiene caracteres especiales) |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | `*` (o URL específica de Railway)

**QA de producción confirmado:**
- ✅ Login / Register
- ✅ Dashboard → crear writer
- ✅ WriterPage (RPG strip, ConfigPanel, Chat)
- ✅ Studio (transición, Brief Setup, pipeline completo con streaming, artefacto)
- ✅ React Router — todas las rutas funcionan (login, dashboard, writer/:id, studio/:writerId)

---

**Learnings reales de Etapa 1 (pitfalls que ocurrieron en orden):**

1. **Railway ignora el Dockerfile si el código no está pusheado** — intenta usar Railpack. Fix: commit + push primero.

2. **TypeScript: imports duplicados en `client.ts`** — `Brief, Piece, ToolUseEvent, ToolResultEvent` importados desde dos lugares. Fix: eliminar del import de `../types`, dejar solo en `../types/studio`.

3. **`vite.config.ts` + `vitest/config` conflicto de tipos** — vitest bundlea su propio vite, causan conflicto cuando `defineConfig` de vitest/config se mezcla con `@vitejs/plugin-react-swc`. Fix: separar en dos archivos.

4. **`bcrypt>=4.0` rompe `passlib 1.7.4`** — `ValueError: password cannot be longer than 72 bytes` en runtime. Fix: `bcrypt>=3.1.0,<4.0.0`.

5. **Healthcheck timeout 30s no alcanza** — langchain/langgraph/anthropic tardan >30s en cold start. Fix: `healthcheckTimeout = 120`.

6. **`startCommand` en `railway.toml` NO expande variables de shell** — Railway lo ejecuta directamente sin shell, `$PORT` llega literal. Fix: sin `startCommand`, usar CMD en Dockerfile en shell form: `CMD uvicorn ... --port ${PORT:-8000}`.

7. **`DATABASE_URL` desde Railway viene como `postgres://`** (no `postgresql+asyncpg://`) — SQLAlchemy no lo reconoce. Fix: normalización en `database.py` + `os.environ.get("DATABASE_URL")` como primera prioridad (antes del config de pydantic-settings).

8. **`StaticFiles(html=True)` no sirve `index.html` para rutas React Router** — solo sirve para paths de directorio, no para `/login` o `/writer/123`. Fix: mount `/assets` + catch-all route `/{full_path:path}` que retorna `FileResponse("frontend/dist/index.html")`.

---

### Etapa 2 — CI/CD Pipeline ✅ COMPLETA (2026-03-18)

Objetivo: tests corren automáticamente en cada PR, Claude revisa diffs antes de llegar a main.

**Qué construimos:**

1. **`.github/workflows/ci.yml`** — corre en PRs a `main` y `sprint-*`:
   - Job `backend-tests`: Python 3.11, `pip install`, `pytest backend/tests/` con `DATABASE_URL=sqlite+aiosqlite:///./test.db`
   - Job `frontend-check`: Node 20, `npm ci`, `vitest run`, `tsc --noEmit`
   - Los dos jobs corren en paralelo

2. **`.github/workflows/pr_review.yml`** — corre en PRs a `main` únicamente:
   - Llama a `scripts/pr_review.py`
   - Postea review como comentario (siempre)
   - Exit 1 solo si detecta 🔴 CRITICAL (puede configurarse como required check)

3. **`scripts/pr_review.py`** — script Python standalone:
   - Fetches diff via GitHub API (Accept: `application/vnd.github.v3.diff`)
   - Llama a `claude-sonnet-4-6` con el diff + system prompt enfocado en los patrones del proyecto
   - Postea comentario con Summary / Issues / Verdict
   - Trunca diffs >30k chars

4. **Auto-deploy**: Railway ya maneja esto — push a `main` → deploy automático. No necesitó workflow adicional.

**Branch protection configurada en GitHub:**
- Ruleset `main protection` → target: `main`
- Required checks: `Backend Tests`, `Frontend Check`
- `Claude Review` no es required — solo informativo

**Secret requerido en GitHub repo:**
- `ANTHROPIC_API_KEY` → Settings → Secrets and variables → Actions

**QA de Etapa 2 confirmado (PR #1 test/ci-validation → main):**
- ✅ Backend Tests — 12/12 passed
- ✅ Frontend Check — vitest + tsc limpios
- ✅ Claude Review — comentó correctamente ("trivial doc change, APPROVED")

**Learnings de Etapa 2:**
- GitHub migró de "Branch protection rules" a "Rulesets" — usar Add ruleset → New branch ruleset → target by pattern `main`
- Los checks solo aparecen como opciones en el ruleset después de haber corrido al menos una vez — primero pushear y abrir un PR de test, luego configurar
- `GITHUB_TOKEN` no necesita setearse como secret — GitHub Actions lo provee automáticamente con `pull-requests: write` si se declara en `permissions:`

---

### Etapa 3 — Migración de DB ⏸ DIFERIDA

**Cuándo:** cuando haya usuarios reales en producción con datos que no podemos borrar. No antes.

Objetivo: pasar de `create_all` a migraciones versionadas con Alembic.

**Por qué dejarlo para el final:** En producción con Railway, la DB de PostgreSQL se crea fresh (no hay datos que migrar). Alembic es importante cuando empezamos a tener usuarios reales con datos reales que no podemos borrar.

**Qué construimos:**

1. **Alembic setup** — `alembic init alembic`, configurar `env.py` con `DATABASE_URL` desde config
2. **Primera migración** — `alembic revision --autogenerate -m "initial schema"` — genera el schema completo
3. **Actualizar `backend/db/database.py`** — reemplazar `create_all` por `alembic upgrade head` en startup
4. **Workflow de migraciones** — para cada cambio de modelo: `alembic revision --autogenerate` + commitear

---

## Decisiones técnicas

| Decisión | Elección | Razón |
|----------|----------|-------|
| Plataforma | Railway | PostgreSQL nativo, deploy desde GitHub, mejor DX que Render |
| Arquitectura | Monorepo / un solo servicio | Más simple, sin CORS cross-origin, un solo lugar para setear vars |
| Frontend deploy | StaticFiles desde FastAPI | No necesita Vercel/Netlify por separado |
| DB local | SQLite sigue igual | Cero cambio al workflow local |
| DB producción | PostgreSQL via DATABASE_URL | Railway lo provee, asyncpg driver |
| Migrations | Etapa 3 (post-deploy) | No hay datos que perder en fresh deploy |

---

## Variables de entorno

| Variable | Local (default) | Producción |
|----------|-----------------|------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/yourwriter.db` | `postgresql+asyncpg://...` (Railway) |
| `SECRET_KEY` | `dev-secret-key` (solo local) | string seguro random |
| `ANTHROPIC_API_KEY` | desde `.env` local | Railway env var |
| `CORS_ORIGINS` | `*` | URL del servicio Railway |
| `ENVIRONMENT` | `development` | `production` |

---

## Archivos que se crean/modifican

```
+ Dockerfile
+ .dockerignore
+ railway.toml
+ backend/config.py
+ .github/workflows/ci.yml
+ .github/workflows/pr_review.yml
+ .github/workflows/deploy.yml
+ scripts/pr_review.py
~ backend/main.py        (CORS desde config, StaticFiles mount)
~ backend/db/database.py (DATABASE_URL desde config, soporte asyncpg)
~ requirements.txt       (+ asyncpg, pydantic-settings)
~ frontend/.env.production (VITE_API_URL=/api)
```

---

## Para el Claude de la próxima sesión

Leer este archivo + ARCHITECTURE.md antes de arrancar.

**Estado actual:**
- Etapa 1 ✅ — App en `https://yourwriter-production.up.railway.app`
- Etapa 2 ✅ — CI/CD activo. Tests en PRs. Claude review en PRs a main.
- Etapa 3 (next) — Alembic migrations

**Próximo: Etapa 3 — Alembic**

El objetivo es pasar de `Base.metadata.create_all` (crea tablas si no existen, no maneja cambios) a migraciones versionadas. Hoy en prod Railway se hace `create_all` en cada startup — funciona porque la DB es nueva, pero cuando haya usuarios reales no podemos borrar y recrear.

Qué hay que construir:
1. `alembic init alembic` — crea `alembic/` con `env.py` y `versions/`
2. Configurar `env.py` para leer `DATABASE_URL` desde `backend.config.settings`
3. `alembic revision --autogenerate -m "initial schema"` — genera la primera migración desde los modelos actuales
4. Reemplazar `create_all` en `backend/db/database.py::init_db()` por `alembic upgrade head`
5. Actualizar `Dockerfile` production stage para correr `alembic upgrade head` antes de arrancar uvicorn

**Pitfalls para Etapa 3:**
- `alembic upgrade head` es síncrono — correrlo en startup antes de uvicorn (no en el lifespan async)
- Con asyncpg, Alembic necesita el driver síncrono para autogenerate: `psycopg2` o configurar `run_migrations_offline` con URL síncrona
- El `env.py` de Alembic necesita importar todos los modelos para que `autogenerate` los detecte
- En Railway el startup command sería: `alembic upgrade head && uvicorn backend.main:app ...` — cambiar el CMD del Dockerfile
