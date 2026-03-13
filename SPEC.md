# YourWriter — Product Specification

## Vision
A tool that lets anyone create, configure, and evolve their own AI writer — for any purpose (novels, tweets, product specs, blog posts). Users interact through plain conversation. Writers evolve over time, developing unique voices through use. The project also serves as an educational showcase of loop agents and lifelong objectives.

## Target Users
- Non-technical people who need writing help (primary)
- Developers/AI enthusiasts who want to understand agent loops (secondary)

## Core Concepts

### Writer
A user-created AI agent with a specific purpose, personality, and evolving identity. Each user can have multiple writers (e.g., "My Tweet Writer", "Novel Draft Assistant", "Feature Spec Writer").

### Identity System
Each writer has an evolving identity composed of:
- **Purpose** — what kind of writing it does (user-defined)
- **Personality traits** — writing voice and style
- **Emotions** — current emotional palette influencing tone
- **Memories** — accumulated context from past interactions and writing
- **Topics** — areas of expertise/interest

Identity starts from a base template and evolves through:
1. **User interaction** — conversational feedback shapes the writer
2. **Autonomous evolution** — after each writing session, the writer reflects and evolves

### User Constraints
Users can set rules and boundaries for their writer in plain English. These are parsed into structured constraints:
- **Word/length limits** — "Keep tweets under 280 characters", "Chapters should be 2000-3000 words"
- **Audience** — "Write for teenagers", "Professional tone for executives"
- **Genre/style** — "Horror stories only", "Light comedy", "Technical documentation"
- **Tone** — "Formal", "Casual and friendly", "Dark and brooding"
- **Custom rules** — any constraint the user describes naturally

Constraints are visible and editable in the configuration panel. The writer respects them across all interactions.

### Lifelong Objectives
Each writer maintains standing goals (e.g., "Improve at concise hooks", "Develop a warmer tone") that persist across sessions. These evolve based on user feedback and self-reflection. This is a key educational feature — showing users the power of agents with persistent goals.

## Features

### MVP (v1)

#### 1. Writer Management
- Create a new writer (name, purpose, initial style description — in plain English)
- System generates structured configuration from natural language
- View/edit writer configuration
- Delete writer

#### 2. Chat Interface
- Conversational interaction with selected writer
- **Pre-writing**: discuss what to write, provide context, give instructions
- **Writing**: writer produces content using its full identity
- **Post-writing**: iterate on output, refine, adjust — conversationally
- Chat history persisted per writer

#### 3. Identity Evolution (Prominent Feature)
- After writing sessions, writer autonomously reflects and evolves
- **Evolution is front and center in the UI** — not hidden in settings
- Live evolution feed: "Your writer just developed a preference for shorter sentences"
- Before/after comparisons on personality traits
- Evolution timeline — see how the writer has grown over time
- User can see what changed, why, and what triggered it
- Optional: user can accept/reject individual evolutions

#### 4. Configuration Panel
- Visual display of writer's current identity (personality, emotions, memories, topics, objectives)
- **User constraints section** — word limits, audience, genre, tone, custom rules
- Constraints set in plain English, parsed into structured rules, visible and editable
- User can see structured config generated from their plain English input
- Editable — user can manually adjust any aspect

#### 5. Agent Visualization (Educational)
- Visual representation of the agent loop during writing
- Show: which agent is active, what tools it's using, what files/data it's accessing
- Real-time or step-by-step view of the pipeline
- Makes the "magic" transparent and educational

#### 6. Tools
- Web search (built-in)
- File reading/writing (internal — for identity management)
- Additional tools pluggable by developers (MCP-style architecture)

#### 7. User System
- User authentication (simple — email/password or OAuth)
- Each user brings their own Anthropic API key
- Free default key with usage limits for trial
- User data isolation — each user's writers are private

### Future (v2+)
- Multiple LLM provider support
- User-addable tools from UI
- Writer sharing/marketplace
- Collaborative writing (multiple users, one writer)
- Self-hosting package

## Architecture

### Frontend
- **React + Vite + TypeScript**
- Chat interface (main interaction)
- Writer management dashboard
- Configuration panel (sidebar)
- Agent visualization component
- Responsive — works on mobile

### Backend
- **Python + FastAPI**
- REST API + WebSocket (for streaming chat & agent visualization)
- Authentication & user management
- API key management (encrypted storage)

### Agent Layer
- **LangChain + LangGraph**
- Agent graph per writer:
  - Chat agent (conversation management)
  - Writer agent (content generation: outline → draft → refine)
  - Identity evolution agent (reflect → evaluate → evolve)
  - Research agent (web search, context gathering)
  - Memory agent (store, retrieve, consolidate)
- Pluggable tool system (MCP-compatible architecture)

### Database
- **SQLite** — users, writers, configurations, chat history, evolution log
- Zero setup, file-based, perfect for v1 and self-hosting
- Migration path to PostgreSQL if needed later
- **File storage** — generated content, identity snapshots

### LLM
- **Anthropic Claude** (starting provider)
- User-provided API keys
- Default free key with rate limits

## Module Structure
```
backend/
  api/          — FastAPI routes
  services/     — business logic
  models/       — database models
  schemas/      — pydantic schemas
  auth/         — authentication
  db/           — database setup, migrations

frontend/
  src/
    components/ — React components
    pages/      — page-level views
    api/        — backend API client
    stores/     — state management
    types/      — TypeScript types

agents/
  graphs/       — LangGraph definitions
  nodes/        — individual agent nodes
  tools/        — agent tools (search, file, etc.)
  prompts/      — system prompts
  evolution/    — identity evolution logic
  skills/       — progressive skill system

shared/
  schemas/      — shared type definitions
  constants/    — shared constants
```

## Deployment
- Containerized (Docker)
- Deployable to any cloud or self-hosted
- Easy setup for non-technical users (one-click deploy or hosted version)

## Educational Goals
- Show how loop agents work in practice
- Demonstrate lifelong objectives and agent evolution
- Visualize the agent pipeline in real-time
- Open-source codebase as learning resource
