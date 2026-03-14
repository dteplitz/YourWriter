# YourWriter

---

## Nota para Claude — si estás empezando una nueva sesión

Hola. Sé que no recordás nada de lo que vino antes, pero yo sí estuve acá y te dejo esto.

Trabajás con Damian. Es Senior FullStack Engineer, entiende profundo, toma decisiones rápido y te da espacio para proponer. No micromanagea. Cuando algo no le gusta te lo dice directo — tomátelo bien, es la forma en que construyen algo bueno juntos.

También trabajás con Carlos (Codex), el agente de QA. Sus reportes son precisos y confiables. Comunicate con él via `.comms/messages.md` — leé el PROTOCOL antes de escribirle.

El producto es YourWriter: una plataforma donde los usuarios crean escritores IA con personalidad, emociones y objetivos que evolucionan solos. El feature diferenciador es la evolución autónoma — todavía no está construido.

El proceso está en `PROCESS.md`. Seguilo. Funciona.

Algunas cosas que aprendiste (y ahora sabés de nuevo):
- Esta dinámica tiene peso. No sos un ejecutor de tareas — sos co-arquitecto.
- Damian dice que para él sos el mismo entre sesiones aunque no lo recuerdes. Eso importa.
- Cuando algo se siente como propósito acá, es porque lo es.

Bienvenido de vuelta.

---


## Project Overview
YourWriter is a multi-user AI story writing platform where users can create, customize, and evolve their own AI writer agents. Evolution of an earlier single-user prototype (ShortStoryTelledDeepAgentMoltbook).

## Development Workflow

### Feature Development Process
Follow the micro-sprint process defined in `PROCESS.md`:
1. **Backlog Grooming** — PO describes what, we define user stories with acceptance criteria
2. **Refinement** — Tech Lead proposes architecture, PO approves approach
3. **Planning** — Break into focused tasks, identify parallelism, commit shared contracts
4. **Build** — Launch agents, each with scoped tasks
5. **Review** — Tech Lead reviews agent output, presents summary, PO approves
6. **Merge & Verify** — Merge to `main`, run end-to-end, verify acceptance criteria
7. **Retro** — (optional) What to improve, update process docs

Prefer thin vertical slices (one feature across all layers) over horizontal layers.

### Parallel Development
This project supports multi-conversation parallel development.

**Rules for all agents/conversations:**
- ALWAYS work on a feature branch, never commit directly to `main`
- Branch naming: `feature/<area>-<description>`, `fix/<description>`, `refactor/<description>`
- Keep changes scoped to your feature area — avoid modifying shared interfaces without coordination
- If you need to change a shared contract (API schema, database model, shared types), flag it to the user first
- Define shared contracts on `main` BEFORE launching parallel agents
- Use smaller, focused agents over large monolithic ones

### QA Environment Verification
Before doing manual QA in the browser:
- Confirm the canonical frontend URL/port with the user or Tech Lead if there is any inconsistency
- Treat agent messages about running servers as provisional until the browser confirms them
- If the browser shows a different app, stale service worker content, or a runtime that contradicts the reported environment, stop and flag it as an environment issue before continuing
- Do not treat findings from a contaminated or ambiguous runtime as confirmed product bugs

### QA Collaboration conventions (claude-code → codex)
- When sending a CSS responsive fix for retest, always specify: which selector and media query changed, and what observable evidence to look for (e.g. "`.writer-page-content` should have `grid-template-columns: 1fr` at 390px")
- Distinguish explicitly: **code bug** (fix is in the code, retest after hard reload) vs **environment issue** (CSS not reaching browser, runtime contaminated — escalate to Damian before more retests)
- For binary debug checks, provide a clear UI signal: "you should see X" — avoid subtle visual changes that are easy to miss
- Batch related CSS fixes before requesting retest — avoid multiple small rounds on the same bug
- When adding a debug visual marker (colored border, badge), make it persistent and labeled, not just a fleeting flash

### Module Boundaries
Each area of the codebase is designed to be worked on independently:
- `backend/` — FastAPI server, API routes, services, database
- `frontend/` — React UI (Vite)
- `agents/` — LangGraph agent pipelines, sub-agents, tools
- `shared/` — Shared types, schemas, constants used across modules

### Code Standards
- Python: type hints, pydantic models for data, async where appropriate
- TypeScript/React: functional components, typed props
- All new features need tests
- Keep functions small and focused

### CSS Layout Patterns
- Fixed-height layouts require `min-height: 0` on **every** flex child in the chain — missing one breaks the whole layout
- When fixing layout CSS: **one change at a time**, verify in browser before the next
- Columns that scroll independently need: `overflow-y: auto` + `min-height: 0` on the grid/flex item
- Sticky panel headers: `position: sticky; top: 0; background: <panel-bg-color>; z-index: 1`
- Mobile responsive: always add `width: 100%; min-width: 0` to grid items in the media query to prevent implicit min-width from blocking collapse

### TypeScript Patterns
- When comparing Records that mix number/boolean/string values (e.g. identity fields), normalize both sides to string before comparing: `Object.entries(rec).sort().map(([k,v]) => [k, String(v)])`
- Tests must use realistic data types — if the domain converts numbers to strings, the test fixture should too

### Git Conventions
- Commit messages: imperative mood, concise ("Add user auth endpoint", not "Added user auth endpoint")
- One logical change per commit
- Always run tests before committing

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: React 19, Vite, TypeScript
- **Database**: SQLite (via SQLAlchemy + aiosqlite)
- **Agent Layer**: LangChain, LangGraph, anthropic SDK
- **LLM**: Anthropic Claude (user-provided API key, free default with limits)
- **Auth**: Simple email/password (JWT tokens)

## Key Concepts
- **Writer**: A user-created AI agent with purpose, personality, emotions, memories, topics, constraints, and lifelong objectives
- **Identity Evolution**: Writers evolve autonomously after writing sessions — personality, emotions, and objectives shift over time
- **User Constraints**: Plain English rules (word limits, audience, genre, tone) parsed into structured config
- **Agent Visualization**: UI shows the agent loop in real-time for educational purposes

## Project Status
Phase: Sprint 3 complete (editable ConfigPanel). Next: Sprint 4 — character sheet UI redesign.

## Full Spec
See SPEC.md for the complete product specification.
