# Sprint 5.5 — Deploy

*Plataforma elegida: **Railway***
*Enfoque: monorepo, un solo servicio (backend sirve el frontend como static files)*

---

## Etapas

### Etapa 1 — Publicar la app (front + back en Railway)

Objetivo: la app accesible en una URL pública. Un solo servicio Railway que sirve tanto la API como el frontend buildeado.

**Qué construimos:**

1. **`backend/config.py`** — settings centralizadas con `pydantic-settings`:
   - `DATABASE_URL` (default: SQLite local, postgres en prod)
   - `SECRET_KEY` (JWT signing)
   - `CORS_ORIGINS` (lista de orígenes permitidos)
   - `ANTHROPIC_API_KEY`
   - `ENVIRONMENT` ("development" | "production")

2. **`backend/main.py`** — actualizar CORS para usar config, agregar StaticFiles mount:
   ```python
   # Al final, después de todos los routes:
   app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
   ```
   El catch-all `html=True` hace que React Router funcione correctamente.

3. **`frontend/.env.production`** — `VITE_API_URL=/api` (relativo, porque frontend y backend van a vivir en el mismo origen)

4. **`Dockerfile`** — multi-stage:
   - Stage 1 (node): `npm ci && npm run build` → genera `frontend/dist/`
   - Stage 2 (python): instala deps, copia todo, `CMD uvicorn backend.main:app`

5. **`.dockerignore`** — excluir `node_modules/`, `__pycache__/`, `.venv/`, `data/`

6. **`railway.toml`** — Railway build + start config:
   ```toml
   [build]
   builder = "DOCKERFILE"

   [deploy]
   startCommand = "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
   ```

7. **`requirements.txt`** — agregar `asyncpg` y `pydantic-settings`

**Lo que Damian hace en Railway (una sola vez):**
1. Crear proyecto nuevo en railway.app → "Deploy from GitHub repo" → seleccionar `dteplitz/YourWriter`
2. Agregar PostgreSQL service (botón "+ New" → Database → PostgreSQL)
3. En el servicio principal, setear variables de entorno:
   - `DATABASE_URL` → copiar desde el PostgreSQL service (Railway lo genera)
   - `SECRET_KEY` → cualquier string largo random
   - `ANTHROPIC_API_KEY` → tu key
   - `CORS_ORIGINS` → la URL de Railway que te asigna (o `*` para empezar)
4. Trigger deploy → en ~3 minutos la app está en `https://yourwriter-xxx.up.railway.app`

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

**Etapa 1 es completamente autónoma** — todo código, sin intervención de Damian hasta el momento de crear el proyecto en Railway y setear las env vars (que son 5 minutos de clicks).

**Pitfalls conocidos:**
- `StaticFiles` debe montarse DESPUÉS de todos los routes de la API, o va a interceptar las requests
- React Router necesita que el servidor sirva `index.html` para cualquier ruta que no sea un archivo — `html=True` en StaticFiles lo maneja
- `DATABASE_URL` de Railway viene como `postgresql://` pero asyncpg necesita `postgresql+asyncpg://` — hacer el replace en config.py
- En Railway, el puerto lo provee la env var `$PORT` — no hardcodear 8001
- El Dockerfile debe buildear el frontend ANTES de copiar el backend, para que `frontend/dist/` exista cuando FastAPI arranca
