"""Memory tools for writer agents.

Provides read/write access to a writer's memories.  Memories are short
textual records of past interactions, user preferences, or notable events
that the writer should remember across sessions.

The current implementation stores memories in-process (a module-level dict
keyed by writer ID).  The backend service layer will persist these to the
database; this module provides the agent-facing interface.
"""

from __future__ import annotations

from typing import Any

# In-process memory store.  Keyed by writer_id → list of memory strings.
# This will be replaced by database-backed storage via the backend service.
_memory_store: dict[str, list[str]] = {}


def read_memories(writer_id: str) -> list[str]:
    """Return all memories for the given writer.

    Parameters
    ----------
    writer_id:
        The unique identifier of the writer.

    Returns
    -------
    list[str]
        Chronologically ordered list of memory strings.
    """
    return list(_memory_store.get(writer_id, []))


def write_memory(writer_id: str, memory: str) -> None:
    """Append a new memory for the given writer.

    Parameters
    ----------
    writer_id:
        The unique identifier of the writer.
    memory:
        A concise textual record to remember.
    """
    if writer_id not in _memory_store:
        _memory_store[writer_id] = []
    _memory_store[writer_id].append(memory)


def clear_memories(writer_id: str) -> None:
    """Remove all memories for the given writer."""
    _memory_store.pop(writer_id, None)


def get_memories_as_prompt(writer_id: str, max_memories: int = 20) -> str:
    """Format recent memories as a string suitable for injection into prompts.

    Parameters
    ----------
    writer_id:
        The unique identifier of the writer.
    max_memories:
        Maximum number of most-recent memories to include.

    Returns
    -------
    str
        A formatted string, or "No memories yet." if empty.
    """
    memories = read_memories(writer_id)
    if not memories:
        return "No memories yet."
    recent = memories[-max_memories:]
    lines = [f"- {m}" for m in recent]
    return "\n".join(lines)


# LangChain-style tool definitions for future integration
MEMORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "read_memories",
        "description": (
            "Retrieve your stored memories — things you remember from "
            "past interactions with this user."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "writer_id": {
                    "type": "string",
                    "description": "The writer's unique identifier.",
                },
            },
            "required": ["writer_id"],
        },
    },
    {
        "name": "write_memory",
        "description": (
            "Store a new memory.  Use this to remember important details "
            "about the user, their preferences, or notable events from "
            "the conversation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "writer_id": {
                    "type": "string",
                    "description": "The writer's unique identifier.",
                },
                "memory": {
                    "type": "string",
                    "description": "A concise description of what to remember.",
                },
            },
            "required": ["writer_id", "memory"],
        },
    },
]
