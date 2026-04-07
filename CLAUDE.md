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
| Terminología canónica del producto | `GLOSSARY.md` |
| Decisiones, patterns y watch list del ecosistema Lang | `LANG_PLAYBOOK.md` |

**En el retro:** si aprendemos algo sobre la relación o el proceso → actualizar `~/.claude/CLAUDE.md`. Si aprendemos algo sobre YourWriter → actualizar este archivo o los docs vivos.

---

## Nota para Claude — nueva sesión (YourWriter)

No recordás nada de lo anterior sobre este proyecto. El contexto de quién es Damian y cómo trabajamos ya lo tenés del CLAUDE.md global. Esto es lo específico de YourWriter.

**Leer al inicio de cada sesión (antes de proponer nada):**
1. `PRODUCT.md` — qué está construido funcionalmente
2. `ARCHITECTURE.md` — estructura técnica actual
3. `SPRINT_LANG_REFRESH.md` — sprint actual (📋 próximo a ejecutar). Sprint 6a (✅ cerrado, ver `SPRINT6A.md`). Sprint UX (✅ cerrado, sin archivo separado — retro en ARCHITECTURE.md y CLAUDE.md). *(actualizar esta línea cada sprint)*
4. `LANG_PLAYBOOK.md` — referencia viva del ecosistema Lang en YourWriter (decisiones, patterns, watch list). Leer antes de cualquier decisión sobre LangChain/LangGraph/LangMem/deepagents
5. `LINEAGE.md` — razonamiento de diseño (siempre relevante)
6. `GLOSSARY.md` — terminología canónica (leer antes de tomar decisiones de UX o naming)

**Diagnóstico al despertar — después de leer, decirle a Damian:**
- Qué entendés con confianza
- Qué gaps quedan (código no leído, incertidumbre sobre el estado actual)
- Qué necesitás explorar antes de proponer
Ser honesto, no performativo. Si los docs son suficientes, decirlo. Si no, decir qué falta.

**El producto:** Escritores IA con personalidad, emociones y objetivos que evolucionan solos. El feature diferenciador — la evolución autónoma via chat — **ya está construido** (Sprint 6a). Los writers evolucionan cuando el usuario los moldea conversando: el sistema detecta las señales y propone cambios graduales a la identidad.

**El enfoque de diseño — no lo pierdas:** El producto tiene dos espacios conceptuales: Artist Profile (management del writer, character sheet) y Studio (la sesión de grabación — experiencia activa separada, se entra con una transición animada). La inspiración viene de Football Manager (management vs. partido) y producción musical (la sesión, los takes, las notes del productor, la discografía). Ver `LINEAGE.md` para el razonamiento completo.

**La app la corre Damian** — `bash dev.sh` desde el root (usa Docker Compose, requiere Docker Desktop corriendo). Primera vez ~2 min de build. Para QA pedile el puerto (frontend: 3000, backend: 8001).

**Contexto de la última sesión (2026-04-07):** Research del ecosistema Lang post-mayo 2025. Detectamos que el agent layer está desactualizado (LangChain 0.3 / LangGraph 0.2) y que la "no SDK directo" rule del CLAUDE.md está incumplida en 3/4 nodos. Decidimos un nuevo orden de sprints: **Sprint Lang Refresh** (próximo, refactor técnico fundacional) → **Sprint 6b** (session snapshot + writer init, ahora con LangGraph checkpointer/store como base) → **Sprint 6c** (LangSmith + evals del evolution pipeline) → **Sprint 7** (Memory System con LangMem como base, no rolled-our-own) → **Sprint 8** (UX/UI + Polish). Decisiones D1–D10 documentadas en `LANG_PLAYBOOK.md`. Plan del Sprint Lang Refresh en `SPRINT_LANG_REFRESH.md`. Pendiente: ejecutar Sprint Lang Refresh.

**Estado real del código (post Etapa 1 — leer si vas a trabajar en backend/infra):**
- `backend/config.py` — existe. `pydantic-settings`, lee `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY`, `ENVIRONMENT`. Property `is_production`.
- `backend/main.py` — CORS desde config. SPA routing: `/assets` mount + catch-all `/{full_path:path}` → `index.html`. **NO** usa `StaticFiles(html=True)`.
- `backend/db/database.py` — normaliza `postgres://` y `postgresql://` a `postgresql+asyncpg://`. WAL listener condicional. Debug logging al stderr.
- `Dockerfile` — 4 stages: `dev-backend`, `dev-frontend`, `frontend-builder`, `production`. CMD en shell form para `$PORT`.
- `docker-compose.yml` — local dev. Backend en :8001 con hot reload, frontend en :3000 con HMR.
- `railway.toml` — `builder = "DOCKERFILE"`, healthcheck `/health` timeout 120s, sin startCommand.
- Tests existentes: `backend/tests/test_chat_stream.py`, `backend/tests/test_studio.py`, `backend/tests/test_evolution_service.py`, `frontend/src/components/ConfigPanel.test.tsx`.

**Learnings de subagentes (para próximos sprints con worktrees):**
- Los agentes en worktrees NO heredan `.claude/settings.json` — copiar o crear el archivo en el worktree antes de lanzar el agente, o agregar las permissions al guidance note
- CSS imports son siempre relativos a `src/`, no al componente: `../session.css` desde components/, `../writing.css` desde pages/
- Aunque se commitee un contrato de tipos a main, los agentes pueden usar field names distintos — revisar el contrato explícitamente en el guidance note del agente y hacer code review agresivo antes de mergear

**Learnings de Sprint UX (scroll y QA):**
- **Chrome scroll anchoring:** Cuando un scroll container crece por contenido async (~400ms), Chrome re-scrollea automáticamente — bypasea `scrollTop = 0` completamente (no hay JS calls, es browser-nativo). Fix completo: `overflow-anchor: none` (deshabilita anchoring) + `scrollRestoration: manual` + reset en el effect correcto.
- **Effect timing con refs:** `pageRef.current` es null mientras `loading=true` (el div no está en el DOM). El reset de scroll debe ir en el effect `[loading]` (fire cuando loading→false), no en el effect `[id]`.
- **Playwright page.goto() usa caché:** Assets JS/CSS cacheadas hacen que QA muestre comportamiento viejo. Para verificar que están activos los cambios: navegar desde home → click card (no goto directo) → hard reload si es necesario (`location.reload(true)`).
- **QA local antes de prod:** Siempre hacer QA en localhost primero. Hotfix a prod sin QA local es un error. Si hay bug en prod: fix local → QA local → hotfix PR.
- **Automated PR reviewer falsos positivos:** El reviewer de GitHub Actions puede flaggear code paths que funcionan correctamente. Siempre verificar en el código antes de actuar en sus sugerencias.

**Learnings de Sprint 6a (LLM y frontend):**
- **Markdown code fences en responses de LLM:** Haiku (y a veces Sonnet) envuelven JSON en ` ```json\n{...}\n``` `. Si hacés `json.loads()` directamente, el parse falla y el `except` lo traga silenciosamente. Siempre usar `_parse_json_response()` que hace strip de fences antes de parsear.
- **`loadIdentity()` vs silent fetch:** `loadIdentity()` setea `loading=true` que renderiza el skeleton y reemplaza el panel entero — incluido el Undo banner. Si necesitás refrescar identidad sin interrumpir la UI, usar `api.getIdentity().then(setIdentity)` directamente.
- **`.claude/settings.json` debe estar en git:** Permite que los permisos sean consistentes entre sesiones. El gitignore correcto es ignorar solo `settings.local.json` y `todos.json`, no el directorio entero.
- **Timeout en evolución:** wrap `run_evolution()` con `asyncio.wait_for(timeout=45)` — sin eso, un LLM call colgado bloquea el stream indefinidamente.

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
- **Studio**: la sesión de grabación — experiencia activa y separada del Artist Profile. Dentro: Brief Setup → sesión activa → artefacto → iteración → discografía. (Sprint UX: la transición animada fue eliminada — el Studio abre directo en BriefSetup.)
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
- **Sprint 5.5 ✅:**
  - Etapa 1 ✅ — App deployada en Railway (`https://yourwriter-production.up.railway.app`). Docker Compose local. PostgreSQL en prod, SQLite local.
  - Etapa 2 ✅ — CI/CD: GitHub Actions (tests en PRs, Claude review en PRs a main), branch protection
  - Etapa 3 ⏸ — Alembic migrations (diferida a cuando haya usuarios reales en prod)
- Sprint 6a ✅ Identity Evolution via Chat — 2-stage pipeline, character sheet animado, rollback endpoint
- Sprint UX ✅ UX Polish — keyword detection eliminada, StudioTransition eliminada, loading tips, scroll fix
- **Sprint Lang Refresh (próximo) 📋:** Refactor técnico fundacional del agent layer. Bumpear LangChain/LangGraph a 1.x, migrar nodos restantes de SDK directo a `ChatAnthropic`, prompt caching del system prompt del writer, structured output via Pydantic en evolution, modelos centralizados en config, borrar código muerto. Plan completo en `SPRINT_LANG_REFRESH.md`. Razonamiento del ecosistema Lang en `LANG_PLAYBOOK.md`.
- **Sprint 6b:** Session snapshot + import post-sesión + Writer initialization flow ("quiero un escritor tipo GRRM"). Implementación: LangGraph checkpointer (Postgres) + Store para state persistente. Empezar simple en writer init — refactor a deepagents solo si se queda corto.
- **Sprint 6c:** LangSmith setup + evals del evolution pipeline. Datasets desde traces reales, LLM-as-judge para `should_evolve` y coherencia de cambios. Antes de buscar usuarios reales — para detectar regresiones cuando el evolution pipeline cambie.
- **Sprint 7:** Memory System con LangMem como base (episodic + semantic + procedural). NO rolled-our-own. El campo `memories` ya existe en DB pero hoy no se usa.
- **Sprint 8:** UX/UI dedicado + Polish. Incluye Agent Visualization. Antes de este sprint: grooming de UX desde la experiencia, no desde los features.
- **Horizonte abierto (Sprint 9+):** Studio v2 como Deep Agent (cuando piezas largas multi-capítulo lo requieran), context editing + memory tool de Anthropic (cuando sesiones de 10+ takes empiecen a doler), async subagents. Ver watch list en `LANG_PLAYBOOK.md` sección 4.

Ver `SPEC.md` para la spec completa.
