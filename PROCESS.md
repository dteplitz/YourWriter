# YourWriter — Development Process

## Roles

| Role | Who | Responsibilities |
|------|-----|-----------------|
| **Product Owner (PO)** | Damian | Vision, priorities, acceptance criteria, final approval |
| **Tech Lead** | Claude (main conversation) | Architecture, task breakdown, agent coordination, code review, merging |
| **Developers** | Subagents | Focused implementation tasks, tests |

## Sprint Cycle

We work in **micro-sprints** — one feature per cycle, designed for a single conversation session. Each sprint follows these ceremonies:

### 1. Backlog Grooming (PO-driven)
**When:** Start of session or when choosing what to build next.
**What happens:**
- PO describes what they want (plain English)
- Tech Lead asks clarifying questions
- Together, define **user stories** with acceptance criteria
- Prioritize: what's the next most valuable thing?

**Output:** One or more user stories in this format:
```
As a [user], I want to [action], so that [value].
Acceptance criteria:
- [ ] ...
- [ ] ...
```

### 2. Refinement (Tech Lead-driven)
**When:** After a user story is selected for the sprint.
**What happens:**
- Tech Lead analyzes the codebase and proposes an architecture/approach
- Identifies which files/modules are affected
- Flags risks, dependencies, or unknowns
- PO reviews and approves the approach

**Output:** A brief design doc (in conversation, not a file) covering:
- What changes where
- API contracts (if cross-module)
- Edge cases considered

### 3. Planning (Tech Lead-driven)
**When:** After refinement is approved.
**What happens:**
- Tech Lead breaks the story into **tasks** (small, focused, one per agent)
- Identifies which tasks can run in parallel vs sequential
- Commits shared contracts to `main` if needed (before agents start)
- PO confirms the plan

**Output:** Task list with:
- Task description
- Agent scope (which files/module)
- Dependencies (what must finish first)
- Parallel grouping

### 4. Build (Agents)
**When:** After planning is confirmed.
**What happens:**
- Tech Lead launches agents (parallel where possible)
- Each agent works on one focused task
- Tech Lead monitors progress, handles blockers

**Rules:**
- Agents work on feature branches
- Each agent gets a clear, scoped prompt
- Agents write tests for their code

### 5. Review (Tech Lead + PO)
**When:** After agents complete.
**What happens:**
- Tech Lead reviews agent output for:
  - Correctness (does it work?)
  - Consistency (do modules align?)
  - Quality (clean code, no hacks?)
- Tech Lead fixes integration issues
- Tech Lead presents a summary to PO:
  - What was built
  - Key decisions made
  - Any deviations from plan
- PO reviews and accepts or requests changes

**Output:** Approved code ready to merge.

### 6. Merge & Verify
**When:** After PO approval.
**What happens:**
- Tech Lead merges to `main`
- Runs the app end-to-end
- Verifies acceptance criteria are met
- Pushes to remote

### 7. Retro (Quick)
**When:** End of sprint (optional, when useful).
**What happens:**
- What went well?
- What should we change?
- Update CLAUDE.md or PROCESS.md if we learn something

## Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Product spec | `SPEC.md` | Full product vision and feature list |
| Dev process | `PROCESS.md` | This file — how we work |
| Agent guidelines | `CLAUDE.md` | Rules all agents follow |
| Backlog | Conversation | User stories discussed and prioritized live |

## Principles

1. **PO decides what, Tech Lead decides how** — Damian sets priorities and acceptance criteria, Claude proposes architecture and implementation
2. **Small batches** — One feature per sprint. Ship it, verify it, then move on
3. **Contracts before code** — Shared types and API shapes committed to `main` before agents build
4. **Transparency** — PO sees the plan before build starts, sees the result before merge
5. **Learn and adapt** — Update this process when we find better ways to work
6. **Working software over perfect software** — Get it running, then improve
