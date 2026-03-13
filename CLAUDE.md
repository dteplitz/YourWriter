# YourWriter

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
Phase: Foundation complete. Next: first vertical slice — "Create a writer and chat with it".

## Full Spec
See SPEC.md for the complete product specification.
