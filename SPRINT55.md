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

### Etapa 2 — CI/CD Pipeline

Objetivo: tests corren automáticamente en cada PR, deploy automático al mergear a main.

**Qué construimos:**

1. **`.github/workflows/ci.yml`** — corre en cada PR:
   - Backend: `python -m pytest backend/tests/`
   - Frontend: `npm run test` + `npx tsc --noEmit`
   - Bloquea merge si falla

2. **`.github/workflows/deploy.yml`** — corre en push a main:
   - Trigger el deploy en Railway via Railway CLI o webhook
   - Railway también puede hacer auto-deploy desde GitHub directamente (más simple)

3. **`.github/workflows/pr_review.yml`** — Claude revisa cada PR:
   - Obtiene el diff del PR
   - Llama a Claude API con el diff + contexto del proyecto
   - Postea review como comentario en el PR
   - Si hay issues críticos (seguridad, data loss, breaking changes), puede bloquear el merge via status check

---

### Etapa 3 — Migración de DB

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

**Estado de Etapa 1:** ✅ COMPLETA. App deployada en `https://yourwriter-production.up.railway.app`. QA confirmado. Código en `main`. Ambiente local usa Docker Compose (`bash dev.sh`).

**Próximo: Etapa 2 — CI/CD Pipeline**

Qué hay que construir:

1. **`.github/workflows/ci.yml`** — corre en cada PR:
   - Backend tests: `python -m pytest backend/tests/`
   - Frontend type check: `npx tsc --noEmit`
   - Bloquea merge si falla

2. **`.github/workflows/pr_review.yml`** — Claude revisa el diff de cada PR:
   - Usa llamada directa a Anthropic API con el diff del PR
   - Postea review como comentario en el PR via `gh` CLI o GitHub API
   - Issues críticos (seguridad, data loss) → bloquea merge via status check

3. **Auto-deploy en Railway**: Railway ya tiene auto-deploy desde GitHub configurado (activo desde Etapa 1 — cada push a `main` dispara un deploy). Solo verificar que esté activo en el dashboard.

**Pitfalls para Etapa 2:**
- Tests de backend en CI deben usar SQLite (variable de entorno `DATABASE_URL` seteada a SQLite en el workflow) — no usar la prod DB
- El `GITHUB_TOKEN` para postear comentarios en PRs viene automático en GitHub Actions — no hay que setearlo como secret
- `ANTHROPIC_API_KEY` sí hay que setearlo como secret del repo para el PR review
- El PR review tiene que ignorar archivos auto-generados (package-lock.json, frontend/dist)
