# YourWriter

*El contexto personal, la forma de trabajo y el proceso de desarrollo están en `~/.claude/CLAUDE.md` (global). Este archivo es específico de YourWriter.*

---

## Dónde vive cada tipo de instrucción

| Tipo | Archivo |
|------|---------|
| Quién es Damian, la relación, cómo colaborar | `~/.claude/CLAUDE.md` (global) |
| Proceso de desarrollo, way of work, principios | `~/.claude/CLAUDE.md` (global) |
| QA con Playwright | `~/.claude/CLAUDE.md` (global) |
| Contexto del producto YourWriter | Este archivo |
| Tech stack, module boundaries, key concepts | Este archivo |
| Estado del proyecto, sprint actual | Este archivo |
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

**Leer siempre al inicio:**
1. `PRODUCT.md` — qué está construido funcionalmente
2. Sprint actual: **Sprint 6b** → `SPRINT6B.md` *(actualizar esta línea cada sprint)*

**Leer según el task (no siempre):**
- Decisiones Lang/LangGraph/LangMem → `LANG_PLAYBOOK.md`
- Decisiones de diseño/UX/naming → `LINEAGE.md` + `GLOSSARY.md`
- Estado técnico detallado → `ARCHITECTURE.md`

**Diagnóstico al despertar — después de leer, decirle a Damian:**
- Qué entendés con confianza
- Qué gaps quedan (código no leído, incertidumbre sobre el estado actual)
- Qué necesitás explorar antes de proponer
Ser honesto, no performativo. Si los docs son suficientes, decirlo. Si no, decir qué falta.

**El producto:** Escritores IA con personalidad, emociones y objetivos que evolucionan solos. La evolución autónoma via chat **ya está construida** (Sprint 6a) — los writers evolucionan cuando el usuario los moldea conversando.

**El enfoque de diseño:** Dos espacios: Artist Profile (management del writer) y Studio (la sesión de grabación). Inspiración: Football Manager + producción musical. Ver `LINEAGE.md` para el razonamiento completo.

**La app la corre Damian** — `bash dev.sh` desde el root (Docker Compose, requiere Docker Desktop). Frontend: 3000, backend: 8001.

---

## Project Overview
YourWriter es una plataforma multi-usuario donde los usuarios crean, customizan y evolucionan sus propios escritores IA.

---

## GitHub
Repo: `dteplitz/YourWriter` — usar GitHub MCP para PR reviews, crear PRs al cierre de sprint, explorar historial de archivos.

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
- Backend (sessions, auth, service pattern, server restart): `.agents/backend.md`

---

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: React 19, Vite, TypeScript
- **Database**: PostgreSQL (local + prod) via SQLAlchemy async + asyncpg. SQLite solo en tests.
- **Agent Layer**: LangChain, LangGraph, Anthropic SDK
- **Auth**: Email/password simple (JWT)

---

## Key Concepts
- **Writer**: agente IA con purpose, personality, emotions, memories, topics, constraints, lifelong objectives
- **Artist Profile**: el espacio de management del writer — character sheet, traits, emotions, constraints, objectives.
- **Studio**: la sesión de grabación — Brief Setup → sesión activa → artefacto → iteración → discografía.
- **Identity Evolution**: los writers evolucionan autónomamente después de cada sesión (Sprint 6a)
- **User Constraints**: reglas en plain English parseadas a config estructurada
- **Discografía / Pieces Library**: las piezas escritas en el Studio se acumulan como una discografía del writer

---

## Project Status

Sprints 1–Lang Refresh ✅ — historial completo en `ARCHITECTURE.md`.

- **Sprint 6b** 🔄 Session entity + Post-sesión import. Plan en `SPRINT6B.md`. Slice 0 ✅ (Postgres local, PR #11), Slice 1 ✅ (PR #12, `StudioSession`/`StudioTake`, session_repository, stream plumbing), Slice 2 ✅ (post-session import flow backend + frontend + QA). Próximo: Slice 3 (checkpointer).
- **Sprint 6b.5** ⏳ Writer initialization flow conversacional (reemplaza CreateWriterModal).
- **Sprint 6c** ⏳ LangSmith + evals del evolution pipeline.
- **Sprint 7** ⏳ Memory System (LangMem — episodic, semantic, procedural).
- **Sprint 8** ⏳ UX/UI dedicado + Polish + Agent Visualization.
- **Sprint 9+** ⏳ Studio v2 deep agent, context editing, async subagents. Ver `LANG_PLAYBOOK.md`.

---

## Reglas de mantenimiento de este archivo

- **Cap: 5KB.** Checkearlo en cada retro. Si supera el límite, extraer antes de mergear.
- **Session context nunca acá.** El contexto de la última sesión va en el sprint doc, no acá.
- **Learnings: solo en memoria.** Nunca duplicar acá lo que ya está en un archivo de memoria.
- **Al cierre de sprint:** comprimir la entrada del sprint a 1 línea en Project Status.
