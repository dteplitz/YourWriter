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
Merge to `main` → Damian does quick visual smoke test (layout, animations, obvious UI bugs) → if it passes, escalate to QA agent → push to remote.

**When to ask Damian to test vs escalate to Carlos:** Ask Damian when it's something visual/interactive that would take Carlos many rounds (e.g., animations, complex flows). Escalate to Carlos for systematic functional QA. Don't abuse Damian's time — only when it genuinely saves rounds.

### 7. Retro (optional, when useful)
- What went well / what to change
- Update `CLAUDE.md` or `PROCESS.md` if we learned something
- Save conventions to `.agents/` templates
- Include Carlos — send retro summary via `.comms/messages.md`
- Update the "Nota para Claude" in `CLAUDE.md` — enrich it with sprint learnings (technical, process, and human). Goal: each new session starts with more depth than the last.
- Archive `.comms/messages.md` — move sprint messages to `.comms/archive/sprint-N.md`, keep only current sprint messages.

## Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Product spec | `SPEC.md` | Full product vision |
| Dev process | `PROCESS.md` | This file |
| Agent guidelines | `CLAUDE.md` | Rules all agents follow |
| Agent templates | `.agents/*.md` | Reusable agent profiles |
| Comms | `.comms/messages.md` | Inter-agent messages (current sprint only) |
| Comms archive | `.comms/archive/` | Historical messages by sprint |

## Principles

1. **Damian co-decides how** — Claude proposes, Damian challenges and approves
2. **Small batches** — one feature per sprint
3. **Contracts before code** — shared types committed to `main` before agents build
4. **Transparency** — PO sees plan before build, result before merge
5. **Learn and adapt** — update this process when we find better ways
6. **Working software over perfect software**
