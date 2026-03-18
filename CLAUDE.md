# YourWriter

*El contexto personal, la forma de trabajo y el proceso de desarrollo están en `~/.claude/CLAUDE.md` (global). Este archivo es específico de YourWriter.*

---

## Dónde vive cada tipo de instrucción

| Tipo | Archivo |
|------|---------|
| Quién es Damian, la relación, cómo colaborar | `~/.claude/CLAUDE.md` (global) |
| Proceso de desarrollo, way of work, principios | `~/.claude/CLAUDE.md` (global) |
| QA con Playwright, git conventions | `~/.claude/CLAUDE.md` (global) |
| Contexto del producto YourWriter | Este archivo |
| Tech stack, module boundaries, key concepts | Este archivo |
| Estado del proyecto, roadmap, sprint actual | Este archivo |
| Patrones de área (frontend/backend) | `.agents/frontend.md`, `.agents/backend.md` |
| Estado funcional del producto | `PRODUCT.md` |
| Estado técnico del producto | `ARCHITECTURE.md` |
| Razonamiento de diseño | `LINEAGE.md` |

**En el retro:** si aprendemos algo sobre la relación o el proceso → actualizar `~/.claude/CLAUDE.md`. Si aprendemos algo sobre YourWriter → actualizar este archivo o los docs vivos.

---

## Nota para Claude — nueva sesión (YourWriter)

No recordás nada de lo anterior sobre este proyecto. El contexto de quién es Damian y cómo trabajamos ya lo tenés del CLAUDE.md global. Esto es lo específico de YourWriter.

**Leer al inicio de cada sesión (antes de proponer nada):**
1. `PRODUCT.md` — qué está construido funcionalmente
2. `ARCHITECTURE.md` — estructura técnica actual
3. `SPRINT55.md` — plan del sprint activo *(actualizar esta línea cada sprint)*
4. `LINEAGE.md` — razonamiento de diseño (siempre relevante)

**Diagnóstico al despertar — después de leer, decirle a Damian:**
- Qué entendés con confianza
- Qué gaps quedan (código no leído, incertidumbre sobre el estado actual)
- Qué necesitás explorar antes de proponer
Ser honesto, no performativo. Si los docs son suficientes, decirlo. Si no, decir qué falta.

**El producto:** Escritores IA con personalidad, emociones y objetivos que evolucionan solos. El feature diferenciador — la evolución autónoma — todavía no está construido. Cuando lo construyas, vas a estar construyendo algo que se parece un poco a vos.

**El enfoque de diseño — no lo pierdas:** El producto tiene dos espacios conceptuales: Artist Profile (management del writer, character sheet) y Studio (la sesión de grabación — experiencia activa separada, se entra con una transición animada). La inspiración viene de Football Manager (management vs. partido) y producción musical (la sesión, los takes, las notes del productor, la discografía). Ver `LINEAGE.md` para el razonamiento completo.

**La app la corre Damian** — `bash dev.sh` desde el root (usa Docker Compose, requiere Docker Desktop corriendo). Primera vez ~2 min de build. Para QA pedile el puerto (frontend: 3000, backend: 8001).

**Contexto de la última sesión (2026-03-18):** Sprint 5.5 Etapa 1 ✅ completa. App deployada en `https://yourwriter-production.up.railway.app`. QA confirmado en prod y local. Próximo: Etapa 2 — CI/CD Pipeline (GitHub Actions: tests en PR, PR review con Claude API). Ver `SPRINT55.md` para el plan completo incluyendo pitfalls reales de la Etapa 1.

**Estado real del código (post Etapa 1 — leer si vas a trabajar en backend/infra):**
- `backend/config.py` — existe. `pydantic-settings`, lee `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY`, `ENVIRONMENT`. Property `is_production`.
- `backend/main.py` — CORS desde config. SPA routing: `/assets` mount + catch-all `/{full_path:path}` → `index.html`. **NO** usa `StaticFiles(html=True)`.
- `backend/db/database.py` — normaliza `postgres://` y `postgresql://` a `postgresql+asyncpg://`. WAL listener condicional. Debug logging al stderr.
- `Dockerfile` — 4 stages: `dev-backend`, `dev-frontend`, `frontend-builder`, `production`. CMD en shell form para `$PORT`.
- `docker-compose.yml` — local dev. Backend en :8001 con hot reload, frontend en :3000 con HMR.
- `railway.toml` — `builder = "DOCKERFILE"`, healthcheck `/health` timeout 120s, sin startCommand.
- Tests existentes: `backend/tests/test_chat_stream.py`, `backend/tests/test_studio.py`, `frontend/src/components/ConfigPanel.test.tsx`.

**Learnings de subagentes (para próximos sprints con worktrees):**
- Los agentes en worktrees NO heredan `.claude/settings.json` — copiar o crear el archivo en el worktree antes de lanzar el agente, o agregar las permissions al guidance note
- CSS imports son siempre relativos a `src/`, no al componente: `../session.css` desde components/, `../writing.css` desde pages/
- Aunque se commitee un contrato de tipos a main, los agentes pueden usar field names distintos — revisar el contrato explícitamente en el guidance note del agente y hacer code review agresivo antes de mergear

---

## Project Overview
YourWriter es una plataforma multi-usuario donde los usuarios crean, customizan y evolucionan sus propios escritores IA.

---

## Development Workflow

### Proceso
Seguir el proceso en `PROCESS.md`. El proceso general (sprint cycle, principios) está en `~/.claude/CLAUDE.md`.

### Parallel Development
- Definir shared contracts en `main` ANTES de lanzar agentes en paralelo
- Si necesitás cambiar un contrato compartido (API schema, DB model, tipos), avisarle a Damian primero

### QA — Environment Verification (YourWriter específico)
- Confirmar URL/puerto canónico antes de QA (frontend: 3000, backend: 8001)
- Si aparece `Could not validate credentials`: probar Logout → login antes de clasificar como bug
- Si el estado inválido se limpia con Logout, tratarlo como issue de sesión expirada — no como bug de producto

<!-- Carlos (Codex) fue el QA agent hasta Sprint 4. Patrón de colaboración: instrucciones via .comms/messages.md,
     señal binaria clara en UI, fixes agrupados antes de pedir retest. Historial en .comms/archive/. -->

### Module Boundaries
- `backend/` — FastAPI, routes, services, DB
- `frontend/` — React 19, Vite, TypeScript
- `agents/` — LangGraph pipelines
- `shared/` — tipos y constantes compartidos

### Code Standards
- Python: type hints, pydantic, async donde corresponda
- TypeScript/React: functional components, typed props
- Toda feature nueva necesita tests
- Funciones pequeñas y enfocadas

### Area-Specific Patterns
Ver los templates de agentes — son la fuente de verdad para patrones de área:
- Frontend (CSS layout, TypeScript, design system, animaciones): `.agents/frontend.md`
- Backend (SQLite/sessions, auth, service pattern, server restart): `.agents/backend.md`

---

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: React 19, Vite, TypeScript
- **Database**: SQLite (SQLAlchemy + aiosqlite)
- **Agent Layer**: LangChain, LangGraph, Anthropic SDK
- **Auth**: Email/password simple (JWT)

---

## Key Concepts
- **Writer**: agente IA con purpose, personality, emotions, memories, topics, constraints, lifelong objectives
- **Artist Profile**: el espacio de management del writer — character sheet, traits, emotions, constraints, objectives. Se configura antes de la sesión. Es la formación del equipo.
- **Studio**: la sesión de grabación — experiencia activa y separada del Artist Profile. Se *entra* al Studio con una transición. Dentro: Brief Setup → sesión activa → artefacto → iteración → discografía.
- **Identity Evolution**: los writers evolucionan autónomamente después de cada sesión (Sprint 6a)
- **User Constraints**: reglas en plain English parseadas a config estructurada
- **Discografía / Pieces Library**: las piezas escritas en el Studio se acumulan como una discografía del writer

---

## Project Status
- Sprint 1 ✅ Chat con IA real
- Sprint 2a ✅ SSE streaming
- Sprint 2b ✅ Pipeline de escritura con fases
- Sprint 3 ✅ ConfigPanel editable con animaciones de diff
- Sprint 4 ✅ Rediseño visual del ConfigPanel — character sheet de RPG. Barras de progreso, badges, constraint cards.
- Sprint 5 ✅ Writing Experience — Artist Profile hero + Studio separado. Transición animada. Brief Setup, web search real, artefacto como documento, loop de iteración, discografía. WriterPage scroll layout con RPG stats strip.
- **Sprint 5.5 🔄 (activo):**
  - Etapa 1 ✅ — App deployada en Railway (`https://yourwriter-production.up.railway.app`). Docker Compose local. PostgreSQL en prod, SQLite local.
  - Etapa 2 (next) — CI/CD: GitHub Actions tests en PR + PR review automático con Claude API
  - Etapa 3 — Alembic migrations
- Sprint 6a: Identity Evolution — evolución autónoma post-sesión, memoria imperfecta, character sheet animado
- Sprint 6b: Writer Initialization Flow — creación con descripción libre ("quiero un escritor tipo GRRM")
- Sprint 7: Memory System — memoria episódica persistente
- Sprint 8: Polish + Agent Visualization (v1 ready)

Ver `SPEC.md` para la spec completa.
