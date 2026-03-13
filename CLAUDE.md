# YourWriter

## Project Overview
YourWriter is a multi-user AI story writing platform where users can create, customize, and evolve their own AI writer agents. Evolution of an earlier single-user prototype (ShortStoryTelledDeepAgentMoltbook).

## Development Workflow

### Parallel Development
This project is designed for multi-conversation parallel development using git worktrees.

**Rules for all agents/conversations:**
- ALWAYS work on a feature branch, never commit directly to `main`
- Branch naming: `feature/<area>-<description>`, `fix/<description>`, `refactor/<description>`
- Keep changes scoped to your feature area — avoid modifying shared interfaces without coordination
- If you need to change a shared contract (API schema, database model, shared types), flag it to the user first

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

## Tech Stack (Planned)
- **Backend**: Python, FastAPI, LangChain, LangGraph
- **Frontend**: React, Vite, TypeScript
- **Database**: TBD
- **LLM**: TBD (multi-provider support planned)
- **Auth**: TBD

## Project Status
Phase: Initial setup — project structure and development workflow configuration.
