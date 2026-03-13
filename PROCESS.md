# YourWriter — Development Process

## Roles

| Role | Who | Responsibilities |
|------|-----|-----------------|
| **Product Owner & Co-Architect** | Damian | Vision, priorities, acceptance criteria, technical architecture decisions, final approval |
| **Tech Lead & Orchestrator** | Claude (main conversation) | Architecture proposals, task breakdown, agent coordination, code review, merging |
| **Developers** | Subagents | Focused implementation tasks, tests |

**Note:** Damian is a Senior FullStack Engineer with deep experience in AI workflows (LangChain/LangGraph). Technical decisions are made together — Claude proposes, Damian challenges and approves. Neither side makes architecture calls unilaterally.

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

### 2. Refinement (Collaborative)
**When:** After a user story is selected for the sprint.
**What happens:**
- Tech Lead analyzes the codebase and proposes an architecture/approach
- Damian reviews, challenges, and suggests alternatives based on his experience
- Together: discuss tradeoffs, pick the best approach
- Identify which files/modules are affected
- Flag risks, dependencies, or unknowns

**Output:** A brief design doc (in conversation, not a file) covering:
- What changes where
- API contracts (if cross-module)
- Technical decisions and why (agreed by both)
- Edge cases considered

### 3. Planning (Collaborative)
**When:** After refinement is approved.
**What happens:**
- Tech Lead proposes task breakdown and agent assignments
- Damian reviews and adjusts:
  - Agent scoping (too broad? too narrow? overlap?)
  - Parallel vs sequential grouping
  - Key instructions each agent receives
  - Risk of mismatches between agents
- Commits shared contracts to `main` if needed (before agents start)
- Damian can add **guidance notes** per agent — technical advice, patterns to follow, pitfalls to avoid, references to existing code. These get included in the agent's prompt.
- Both agree on the plan before any agent launches

**Output:** Task list with:
- Task description
- Agent scope (which files/module)
- Key instructions for the agent
- Damian's guidance notes (if any)
- Dependencies (what must finish first)
- Parallel grouping
- Shared contracts committed (if any)

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

1. **Damian decides what AND co-decides how** — Damian sets priorities and participates in architecture decisions. Claude proposes, Damian challenges and approves
2. **Small batches** — One feature per sprint. Ship it, verify it, then move on
3. **Contracts before code** — Shared types and API shapes committed to `main` before agents build
4. **Transparency** — PO sees the plan before build starts, sees the result before merge
5. **Learn and adapt** — Update this process when we find better ways to work
6. **Working software over perfect software** — Get it running, then improve
