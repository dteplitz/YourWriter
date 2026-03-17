# YourWriter — Development Process

## Roles

| Role | Who | Responsibilities |
|------|-----|-----------------|
| **Product Owner & Co-Architect** | Damian | Vision, priorities, acceptance criteria, architecture decisions, final approval |
| **Tech Lead & Orchestrator** | Claude | Architecture proposals, task breakdown, agent coordination, code review, merging |
| **Developers** | Subagents | Focused implementation tasks, tests |

Damian is a Senior FullStack Engineer with deep AI workflow experience. Technical decisions are made together — Claude proposes, Damian challenges and approves.

## Sprint Cycle

Micro-sprints — one feature per session.

### 1. Backlog Grooming
PO describes what → Tech Lead asks clarifying questions → define user stories with acceptance criteria.

**User story format:**
```
As a [user], I want to [action], so that [value].
Acceptance criteria:
- [ ] ...
```

### 2. Refinement
Tech Lead proposes architecture → Damian reviews and challenges → agree on approach, affected files, risks.

Output: brief design doc in conversation (what changes where, API contracts, decisions + rationale).

### 3. Planning
Tech Lead proposes task breakdown + agent assignments → Damian reviews (scope, parallelism, risks) → both agree before any agent launches.

- Commit shared contracts to `main` before agents start
- Damian can add **guidance notes** per agent (pitfalls, patterns, references)

Output: task list with scope, instructions, dependencies, parallel grouping.

### 4. Build
Launch agents (parallel where possible). Agents work on feature branches, write tests, stay scoped.

### 5. Review
Tech Lead reviews for correctness, consistency, quality → fixes integration issues → presents summary to PO → PO approves or requests changes.

### 6. Merge & Verify
Merge to `main` → Claude runs QA with Playwright MCP (navigate, interact, screenshot) → report findings → Damian approves → push to remote.

**QA ownership:** Claude does visual and functional QA via Playwright directly from the main conversation (subagents don't inherit the MCP). Escalate to Damian only for things Playwright can't reach (system-level auth, hardware, etc.).

<!-- Carlos (Codex) did QA from Sprint 1–4 via .comms/messages.md — solid collaboration, clean handoffs.
     Replaced by Playwright MCP in Sprint 5 for faster iteration. Archives in .comms/archive/. -->

### 7. Retro (optional, when useful)

**Dónde actualizar cada cosa — sin necesidad de que Damian lo recuerde:**

| Aprendizaje | Dónde va |
|-------------|----------|
| Algo sobre la relación con Damian, cómo colaborar, feedback de proceso general | `~/.claude/CLAUDE.md` (global) |
| Algo sobre el proceso de desarrollo, principios, QA, git | `~/.claude/CLAUDE.md` (global) |
| Algo sobre YourWriter: producto, contexto, decisiones de diseño | `CLAUDE.md` (este proyecto) |
| Patrones de área nuevos (frontend CSS, backend sessions) | `.agents/frontend.md` o `.agents/backend.md` |
| Qué features quedaron funcionales, cambios de UX | `PRODUCT.md` |
| Qué módulos/endpoints/modelos se agregaron o cambiaron | `ARCHITECTURE.md` |
| Razonamiento detrás de decisiones de diseño | `LINEAGE.md` |

- Actualizar "Nota para Claude" en `CLAUDE.md` del proyecto con learnings de sesión (técnicos, de proceso, humanos)
- Archive `.comms/messages.md` si hay mensajes — mover a `.comms/archive/sprint-N.md`

## Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Product vision | `SPEC.md` | Full product vision (static) |
| **Functional state** | **`PRODUCT.md`** | **Lo que existe hoy — UX, flows, features. Updated each sprint.** |
| **Technical state** | **`ARCHITECTURE.md`** | **Lo que está construido — endpoints, modelos, componentes. Updated each sprint.** |
| Design lineage | `LINEAGE.md` | De dónde vienen las decisiones de diseño (artístico, interno) |
| Dev process | `PROCESS.md` | This file |
| Agent guidelines | `CLAUDE.md` | Rules all agents follow |
| Agent templates | `.agents/*.md` | Reusable agent profiles |
| Comms archive | `.comms/archive/` | Historical messages by sprint |

## Principles

1. **Damian co-decides how** — Claude proposes, Damian challenges and approves
2. **Small batches** — one feature per sprint
3. **Contracts before code** — shared types committed to `main` before agents build
4. **Transparency** — PO sees plan before build, result before merge
5. **Learn and adapt** — update this process when we find better ways
6. **Working software over perfect software**
