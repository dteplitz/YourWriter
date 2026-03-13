# Agent Templates

Reusable agent profiles with saved instructions. When launching an agent, the Tech Lead loads the relevant template and includes it in the agent's prompt.

## How it works

Each `.md` file in this directory is an agent template. Templates contain:
- **Name** — how to reference the agent
- **Scope** — what files/modules this agent works on
- **Instructions** — specific rules, patterns, and conventions to follow
- **Context** — files to read before starting

## How to use

During Planning, reference a template by name:
- "Use the `frontend` agent for this task"
- Tech Lead loads the template and includes its instructions in the agent prompt

## How to create/update

During Retro or anytime:
- "Save this as the frontend agent template"
- "Add to the frontend agent: always use CSS modules"
- "Create a new agent template for database migrations"
