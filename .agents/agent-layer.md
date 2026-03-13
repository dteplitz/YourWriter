# Agent Layer Agent

## Scope
`agents/` — LangGraph graphs, nodes, prompts, tools, evolution system

## Context (read before starting)
- `CLAUDE.md` — project overview and standards
- `agents/graphs/` — existing graph definitions (writer + evolution)
- `agents/evolution/identity.py` — Identity dataclass
- `agents/prompts/system.py` — all system prompts

## Instructions
- LangGraph StateGraph with TypedDict states
- Async node functions
- Anthropic SDK for LLM calls (`anthropic.AsyncAnthropic()`)
- Identity always goes through `Identity.from_dict()` / `to_dict()` — never raw dicts
- Prompts use `.format()` with named placeholders
- Tools are pure functions, no side effects beyond their stated purpose
- Evolution changes must include reasons (for the evolution log)

## Conventions
<!-- Add conventions here as we establish them -->
<!-- Example: - All nodes return only the state keys they modify -->
<!-- Example: - Temperature: 0.3 for analysis, 0.7 for creative writing -->
